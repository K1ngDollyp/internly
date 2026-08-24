from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile, Placement, Assessment, IndustrySupervisor, AuditLog
from app.schemas.siwes_schemas import AssessmentCreate, AssessmentResponse

router = APIRouter(prefix="/assessments", tags=["Assessments"])

@router.post("", response_model=AssessmentResponse)
def create_assessment(
    assessment_in: AssessmentCreate,
    placement_id: int,
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")
        
    supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
    if not supervisor or placement.supervisor_id != supervisor.id:
        raise HTTPException(status_code=403, detail="Forbidden: You are not assigned to this student")
        
    total = (
        assessment_in.punctuality_score +
        assessment_in.technical_score +
        assessment_in.communication_score +
        assessment_in.professionalism_score
    )

    # Check if assessment already exists — update scores
    existing = db.query(Assessment).filter(Assessment.placement_id == placement_id).first()
    if existing:
        existing.punctuality_score = assessment_in.punctuality_score
        existing.technical_score = assessment_in.technical_score
        existing.communication_score = assessment_in.communication_score
        existing.professionalism_score = assessment_in.professionalism_score
        existing.total_score = total
        existing.remarks = assessment_in.remarks
        db.commit()
        db.refresh(existing)
        return existing

    new_assess = Assessment(
        placement_id=placement_id,
        assessor_id=current_user.id,
        punctuality_score=assessment_in.punctuality_score,
        technical_score=assessment_in.technical_score,
        communication_score=assessment_in.communication_score,
        professionalism_score=assessment_in.professionalism_score,
        total_score=total,
        remarks=assessment_in.remarks,
        status="draft"
    )
    db.add(new_assess)
    db.commit()
    db.refresh(new_assess)
    return new_assess

@router.patch("/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(
    assessment_id: int,
    assessment_in: AssessmentCreate,
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    assess = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assess:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    if assess.status == "finalized":
        raise HTTPException(status_code=400, detail="Finalized assessments cannot be updated")
        
    # Verify supervisor ownership
    supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
    if not supervisor or assess.placement.supervisor_id != supervisor.id:
        raise HTTPException(status_code=403, detail="Forbidden: Access Denied")
        
    assess.punctuality_score = assessment_in.punctuality_score
    assess.technical_score = assessment_in.technical_score
    assess.communication_score = assessment_in.communication_score
    assess.professionalism_score = assessment_in.professionalism_score
    assess.total_score = (
        assessment_in.punctuality_score +
        assessment_in.technical_score +
        assessment_in.communication_score +
        assessment_in.professionalism_score
    )
    assess.remarks = assessment_in.remarks
    
    db.commit()
    db.refresh(assess)
    return assess

@router.post("/{assessment_id}/finalize", response_model=AssessmentResponse)
def finalize_assessment(
    assessment_id: int,
    current_user: User = Depends(RoleChecker(["supervisor", "coordinator", "admin"])),
    db: Session = Depends(get_db)
):
    assess = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assess:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    if current_user.role == "supervisor":
        supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
        if not supervisor or assess.placement.supervisor_id != supervisor.id:
            raise HTTPException(status_code=403, detail="Forbidden: Access Denied")
            
    assess.status = "finalized"
    db.commit()
    db.refresh(assess)
    
    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        action="finalize_assessment",
        entity_type="assessment",
        entity_id=assess.id,
        metadata_json={"total_score": assess.total_score}
    )
    db.add(audit)
    db.commit()
    
    return assess

@router.get("/placement/{placement_id}", response_model=AssessmentResponse)
def get_assessment(
    placement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")
        
    # Check permissions
    if current_user.role == "student":
        student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
        if not student_profile or placement.student_id != student_profile.id:
            raise HTTPException(status_code=403, detail="Forbidden: Access Denied")
    elif current_user.role == "supervisor":
        supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
        if not supervisor or placement.supervisor_id != supervisor.id:
            raise HTTPException(status_code=403, detail="Forbidden: Access Denied")
            
    assess = db.query(Assessment).filter(Assessment.placement_id == placement_id).first()
    if not assess:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assess
