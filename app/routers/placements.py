from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile, Organization, Placement, IndustrySupervisor, AuditLog
from app.schemas.siwes_schemas import PlacementSubmit, PlacementResponse, PlacementApproval, OrganizationResponse
from typing import List

router = APIRouter(prefix="/placements", tags=["Placements"])

@router.post("", response_model=PlacementResponse)
def submit_placement(
    placement_in: PlacementSubmit,
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
        
    # Check if student already has a pending or approved placement
    existing_placement = db.query(Placement).filter(
        Placement.student_id == student_profile.id,
        Placement.status.in_(["pending", "approved"])
    ).first()
    if existing_placement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active or pending placement request."
        )

    # Check if organization exists, otherwise create it
    org = db.query(Organization).filter(Organization.name == placement_in.organization_name).first()
    if not org:
        org = Organization(
            name=placement_in.organization_name,
            address=placement_in.organization_address,
            industry=placement_in.organization_industry,
            contact_email=placement_in.organization_email,
            contact_phone=placement_in.organization_phone
        )
        db.add(org)
        db.commit()
        db.refresh(org)

    new_placement = Placement(
        student_id=student_profile.id,
        organization_id=org.id,
        start_date=placement_in.start_date,
        end_date=placement_in.end_date,
        status="pending"
    )
    db.add(new_placement)
    db.commit()
    db.refresh(new_placement)
    
    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        action="submit_placement",
        entity_type="placement",
        entity_id=new_placement.id,
        metadata_json={"organization": org.name}
    )
    db.add(audit)
    db.commit()

    return new_placement

@router.get("/me", response_model=PlacementResponse)
def get_own_placement(
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    placement = db.query(Placement).filter(Placement.student_id == student_profile.id).order_by(Placement.id.desc()).first()
    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No placement request found"
        )
    return placement

@router.get("", response_model=List[PlacementResponse])
def get_all_placements(
    current_user: User = Depends(RoleChecker(["coordinator", "admin"])),
    db: Session = Depends(get_db)
):
    return db.query(Placement).all()

@router.patch("/{placement_id}", response_model=PlacementResponse)
def update_placement_status(
    placement_id: int,
    approval: PlacementApproval,
    current_user: User = Depends(RoleChecker(["coordinator", "admin"])),
    db: Session = Depends(get_db)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement record not found"
        )
    
    status_val = approval.decision.lower()
    if status_val not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be approved or rejected"
        )
        
    placement.status = status_val
    if approval.supervisor_id:
        # Verify the supervisor exists and has the supervisor role
        supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.id == approval.supervisor_id).first()
        if not supervisor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Industry Supervisor not found"
            )
        placement.supervisor_id = supervisor.id
        
    db.commit()
    db.refresh(placement)
    
    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        action=f"placement_{status_val}",
        entity_type="placement",
        entity_id=placement.id,
        metadata_json={"supervisor_id": approval.supervisor_id}
    )
    db.add(audit)
    db.commit()

    return placement

@router.get("/supervisors", response_model=List[dict])
def get_all_supervisors(
    current_user: User = Depends(RoleChecker(["coordinator", "admin"])),
    db: Session = Depends(get_db)
):
    supervisors = db.query(IndustrySupervisor).all()
    results = []
    for s in supervisors:
        results.append({
            "id": s.id,
            "full_name": s.user.full_name,
            "organization_name": s.organization.name if s.organization else "Unassigned",
            "job_title": s.job_title
        })
    return results

@router.get("/organizations", response_model=List[OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_db)
):
    return db.query(Organization).all()
