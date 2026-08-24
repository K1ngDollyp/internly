import os
import hashlib
import secrets
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.core.security import get_password_hash
from app.models.siwes import (
    User, StudentProfile, Placement, PlacementRequest, SupervisorInvitation,
    SupervisorConfirmation, VerificationEvidence, VerificationReview, FieldComparison, StatusHistory,
    Organization, IndustrySupervisor, AuditLog, AcademicSession, Notification
)
from app.schemas.siwes_schemas import (
    PlacementRequestCreate, PlacementRequestUpdate, PlacementRequestResponse,
    SupervisorConfirmationSubmit, EvidenceSubmit, VerificationReviewSubmit,
    InvitationResponse
)
from app.services.ai_service import LogbookAIModel
from typing import List, Optional
import shutil

router = APIRouter(prefix="/verification", tags=["Verification"])

# Set upload directory compatible with Vercel serverless filesystem (/tmp)
UPLOAD_DIR = "/tmp/uploads" if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "uploads"
if not os.path.exists(UPLOAD_DIR):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except Exception:
        UPLOAD_DIR = "/tmp"

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def create_audit_event(db: Session, actor_id: Optional[int], action: str, entity_type: str, entity_id: Optional[int], details: dict):
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=details
    )
    db.add(log)
    db.commit()

def create_in_app_notify(db: Session, recipient_id: int, title: str, message: str, type_str: str = "info"):
    notify = Notification(
        recipient_id=recipient_id,
        title=title,
        message=message,
        type=type_str
    )
    db.add(notify)
    db.commit()

@router.post("/request", response_model=PlacementRequestResponse)
def create_placement_request(
    req_in: PlacementRequestCreate,
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    if not student_profile.is_verified:
        raise HTTPException(status_code=400, detail="Your student profile identity must be verified by a coordinator before submitting placement requests.")

    # Check for active placement or non-rejected requests
    existing = db.query(PlacementRequest).filter(
        PlacementRequest.student_id == student_profile.id,
        PlacementRequest.status.in_(["draft", "submitted", "awaiting_supervisor", "supervisor_confirmed", "evidence_submitted", "under_coordinator_review", "verified", "active"])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending or active placement request.")

    # Auto-associate active session
    sess_id = req_in.session_id
    if not sess_id:
        active_sess = db.query(AcademicSession).filter(AcademicSession.status == "active").first()
        if active_sess:
            sess_id = active_sess.id

    new_req = PlacementRequest(
        student_id=student_profile.id,
        session_id=sess_id,
        proposed_company_name=req_in.proposed_company_name,
        proposed_company_address=req_in.proposed_company_address,
        proposed_company_industry=req_in.proposed_company_industry,
        proposed_company_email=req_in.proposed_company_email,
        proposed_company_phone=req_in.proposed_company_phone,
        proposed_supervisor_name=req_in.proposed_supervisor_name,
        proposed_supervisor_job_title=req_in.proposed_supervisor_job_title,
        proposed_supervisor_email=req_in.proposed_supervisor_email,
        proposed_supervisor_phone=req_in.proposed_supervisor_phone,
        proposed_supervisor_experience=req_in.proposed_supervisor_experience,
        proposed_supervisor_department=req_in.proposed_supervisor_department,
        relationship_to_student=req_in.relationship_to_student,
        conflict_declaration=req_in.conflict_declaration,
        company_representative_name=req_in.company_representative_name,
        company_representative_email=req_in.company_representative_email,
        start_date=req_in.start_date,
        end_date=req_in.end_date,
        duration_weeks=req_in.duration_weeks,
        how_obtained=req_in.how_obtained,
        proposed_duties=req_in.proposed_duties,
        technical_areas=req_in.technical_areas,
        expected_work=req_in.expected_work,
        status="draft"
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)

    # Log initial status history
    history = StatusHistory(
        placement_request_id=new_req.id,
        old_status=None,
        new_status="draft",
        changed_by=current_user.id,
        reason="Draft request created by student"
    )
    db.add(history)
    db.commit()

    return new_req

@router.get("/request/my", response_model=Optional[PlacementRequestResponse])
def get_my_placement_request(
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    return db.query(PlacementRequest).filter(
        PlacementRequest.student_id == student_profile.id
    ).order_by(PlacementRequest.id.desc()).first()

@router.patch("/request/{req_id}", response_model=PlacementRequestResponse)
def update_placement_request(
    req_id: int,
    req_in: PlacementRequestUpdate,
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    req = db.query(PlacementRequest).filter(PlacementRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Placement request not found")

    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile or req.student_id != student_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this request")

    if req.status not in ["draft", "correction_required"]:
        raise HTTPException(status_code=400, detail="Cannot edit a request that is already submitted or under review")

    for field, value in req_in.dict(exclude_unset=True).items():
        setattr(req, field, value)

    # If it was correction_required, reset status to resubmitted
    old_status = req.status
    if old_status == "correction_required":
        req.status = "resubmitted"
        history = StatusHistory(
            placement_request_id=req.id,
            old_status=old_status,
            new_status="resubmitted",
            changed_by=current_user.id,
            reason="Corrections resubmitted by student"
        )
        db.add(history)

    db.commit()
    db.refresh(req)
    return req

@router.post("/request/{req_id}/submit", response_model=dict)
def submit_placement_request(
    req_id: int,
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    req = db.query(PlacementRequest).filter(PlacementRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Placement request not found")

    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile or req.student_id != student_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this request")

    if req.status not in ["draft", "correction_required", "resubmitted"]:
        raise HTTPException(status_code=400, detail="Request is already submitted")

    old_status = req.status
    req.status = "awaiting_supervisor"
    req.submitted_at = datetime.datetime.now(datetime.timezone.utc)

    # Create invitation token
    token = secrets.token_hex(16)
    hashed = hash_token(token)
    invitation = SupervisorInvitation(
        placement_request_id=req.id,
        email=req.proposed_supervisor_email,
        token_hash=hashed,
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        status="active"
    )
    db.add(invitation)

    history = StatusHistory(
        placement_request_id=req.id,
        old_status=old_status,
        new_status="awaiting_supervisor",
        changed_by=current_user.id,
        reason="Submitted and invitation generated"
    )
    db.add(history)
    db.commit()

    # Trigger audit trails and notifications
    create_audit_event(
        db, 
        current_user.id, 
        "SUBMIT_PLACEMENT_REQUEST", 
        "PlacementRequest", 
        req.id, 
        {"proposed_company": req.proposed_company_name, "supervisor": req.proposed_supervisor_name}
    )
    create_in_app_notify(
        db, 
        current_user.id, 
        "Placement Request Submitted", 
        f"Your SIWES placement proposal for {req.proposed_company_name} was successfully submitted. An invite link has been generated for your supervisor.",
        "success"
    )

    return {
        "message": "Placement request submitted successfully",
        "invitation_token": token,
        "invitation_link": f"/#invite/{token}"
    }

@router.get("/invitation/{token}", response_model=InvitationResponse)
def get_invitation_details(token: str, db: Session = Depends(get_db)):
    hashed = hash_token(token)
    invite = db.query(SupervisorInvitation).filter(
        SupervisorInvitation.token_hash == hashed,
        SupervisorInvitation.status == "active"
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation token not found or already used")

    if invite.expires_at < datetime.datetime.utcnow():
        invite.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Invitation token has expired")

    req = invite.placement_request
    student_user = req.student.user
    
    return {
        "id": invite.id,
        "placement_request_id": invite.placement_request_id,
        "email": invite.email,
        "token_hash": invite.token_hash,
        "expires_at": invite.expires_at,
        "status": invite.status,
        "student_name": student_user.full_name,
        "proposed_company_name": req.proposed_company_name
    }

@router.post("/invitation/{token}/accept", response_model=dict)
def accept_invitation_and_register(
    token: str,
    full_name: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    job_title: str = Form(...),
    confirm_statement: bool = Form(...),
    db: Session = Depends(get_db)
):
    if not confirm_statement:
        raise HTTPException(status_code=400, detail="You must confirm the organization affiliation statement to proceed.")

    hashed = hash_token(token)
    invite = db.query(SupervisorInvitation).filter(
        SupervisorInvitation.token_hash == hashed,
        SupervisorInvitation.status == "active"
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    # Create Supervisor account
    existing_user = db.query(User).filter(User.email == invite.email).first()
    if existing_user:
        user = existing_user
    else:
        user = User(
            full_name=full_name,
            email=invite.email,
            password_hash=get_password_hash(password),
            role="supervisor",
            status="active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Check/Create supervisor profile
    sv_profile = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == user.id).first()
    if not sv_profile:
        sv_profile = IndustrySupervisor(
            user_id=user.id,
            job_title=job_title
        )
        db.add(sv_profile)
        db.commit()
        db.refresh(sv_profile)

    # Record Confirmation
    confirm = SupervisorConfirmation(
        placement_request_id=invite.placement_request_id,
        supervisor_id=user.id,
        confirmation_statement=True,
        ip_address="127.0.0.1",
        user_agent="Browser"
    )
    db.add(confirm)

    # Update request status
    req = invite.placement_request
    old_status = req.status
    
    # Optional HR/company representative confirmation transition
    if req.company_representative_email:
        req.status = "awaiting_hr_confirmation"
        req.hr_invitation_token = secrets.token_hex(16)
        reason_str = "Supervisor accepted invitation; awaiting optional HR/company representative confirmation"
    else:
        req.status = "supervisor_confirmed"
        reason_str = "Supervisor accepted invitation and confirmed affiliation"
    
    invite.accepted_at = datetime.datetime.now(datetime.timezone.utc)
    invite.status = "accepted"

    history = StatusHistory(
        placement_request_id=req.id,
        old_status=old_status,
        new_status=req.status,
        changed_by=user.id,
        reason=reason_str
    )
    db.add(history)
    db.commit()

    # Trigger notifications and audit trails
    create_audit_event(
        db, 
        user.id, 
        "SUPERVISOR_ACCEPT_INVITE", 
        "PlacementRequest", 
        req.id, 
        {"supervisor_email": invite.email, "status": req.status}
    )
    create_in_app_notify(
        db, 
        req.student.user_id, 
        "Supervisor Accepted Invitation", 
        f"Your proposed supervisor {user.full_name} has accepted the invitation for your SIWES placement.",
        "success"
    )

    return {"message": "Invitation accepted successfully", "email": invite.email, "hr_invitation_token": req.hr_invitation_token}

@router.post("/request/{req_id}/confirm")
def supervisor_confirm_fields_and_evidence(
    req_id: int,
    evidence_type: str = Form(...),
    title: str = Form(...),
    issuer_name: Optional[str] = Form(None),
    issuer_contact: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    field_confirmations: str = Form(...),  # JSON dict of true/false confirmations
    field_corrections: str = Form(...),      # JSON dict of text corrections
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    import json
    try:
        confirmations = json.loads(field_confirmations)
        corrections = json.loads(field_corrections)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON fields confirmations or corrections")

    req = db.query(PlacementRequest).filter(PlacementRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Placement request not found")

    # Save evidence file if provided
    file_url_val = "/uploads/default_acceptance.pdf"
    if file and file.filename:
        max_size = 5 * 1024 * 1024
        content = file.file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="File too large. Max is 5MB")
        file.file.seek(0)

        file_ext = os.path.splitext(file.filename)[1]
        safe_filename = f"evidence_verify_{req_id}_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}{file_ext}"
        dest_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url_val = f"/uploads/{safe_filename}"

    # Save evidence record
    evidence = VerificationEvidence(
        placement_request_id=req.id,
        submitted_by=current_user.id,
        evidence_type=evidence_type,
        title=title,
        file_url=file_url_val,
        issuer_name=issuer_name,
        issuer_contact=issuer_contact,
        notes=notes,
        status="pending"
    )
    db.add(evidence)

    # Clean old comparisons if any
    db.query(FieldComparison).filter(FieldComparison.placement_request_id == req.id).delete()

    # Compare fields field by field side by side
    fields_to_check = {
        "company_name": (req.proposed_company_name, corrections.get("company_name", req.proposed_company_name) if not confirmations.get("company_name", True) else req.proposed_company_name),
        "company_address": (req.proposed_company_address, corrections.get("company_address", req.proposed_company_address) if not confirmations.get("company_address", True) else req.proposed_company_address),
        "supervisor_name": (req.proposed_supervisor_name, corrections.get("supervisor_name", req.proposed_supervisor_name) if not confirmations.get("supervisor_name", True) else req.proposed_supervisor_name),
        "supervisor_job_title": (req.proposed_supervisor_job_title, corrections.get("supervisor_job_title", req.proposed_supervisor_job_title) if not confirmations.get("supervisor_job_title", True) else req.proposed_supervisor_job_title),
        "start_date": (str(req.start_date), corrections.get("start_date", str(req.start_date)) if not confirmations.get("start_date", True) else str(req.start_date)),
        "end_date": (str(req.end_date), corrections.get("end_date", str(req.end_date)) if not confirmations.get("end_date", True) else str(req.end_date)),
        "duration_weeks": (str(req.duration_weeks), corrections.get("duration_weeks", str(req.duration_weeks)) if not confirmations.get("duration_weeks", True) else str(req.duration_weeks)),
    }

    for f_name, (st_val, sv_val) in fields_to_check.items():
        ai_res = LogbookAIModel.compare_verification_fields(st_val, sv_val)
        
        # If supervisor flagged correction explicitly, set status to CORRECTION
        match_status = "CORRECTION" if not confirmations.get(f_name, True) else ai_res["status"]
        
        fc = FieldComparison(
            placement_request_id=req.id,
            field_name=f_name,
            student_value=st_val,
            supervisor_value=sv_val,
            match_status=match_status
        )
        db.add(fc)

    # Update request status
    old_status = req.status
    req.status = "under_coordinator_review"
    
    history = StatusHistory(
        placement_request_id=req.id,
        old_status=old_status,
        new_status="under_coordinator_review",
        changed_by=current_user.id,
        reason="Evidence and confirmations submitted by supervisor"
    )
    db.add(history)
    db.commit()

    return {"message": "Evidence and confirmation package submitted for review"}

@router.get("/queue", response_model=List[PlacementRequestResponse])
def get_coordinator_queue(
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    return db.query(PlacementRequest).filter(
        PlacementRequest.status != "draft"
    ).order_by(PlacementRequest.submitted_at.desc()).all()

@router.get("/request/{req_id}/detail", response_model=PlacementRequestResponse)
def get_request_verification_detail(
    req_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = db.query(PlacementRequest).filter(PlacementRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Placement request not found")
        
    return req

@router.post("/request/{req_id}/review")
def review_placement_request(
    req_id: int,
    review_in: VerificationReviewSubmit,
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    req = db.query(PlacementRequest).filter(PlacementRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Placement request not found")

    decision_val = review_in.decision.lower()
    if decision_val not in ["approved", "correction_required", "rejected", "escalated"]:
        raise HTTPException(status_code=400, detail="Invalid review decision")

    old_status = req.status
    req.status = decision_val if decision_val != "approved" else "verified"

    # Create VerificationReview
    review = VerificationReview(
        placement_request_id=req.id,
        coordinator_id=current_user.id,
        decision=decision_val,
        reason=review_in.reason
    )
    db.add(review)

    history = StatusHistory(
        placement_request_id=req.id,
        old_status=old_status,
        new_status=req.status,
        changed_by=current_user.id,
        reason=f"Coordinator review decision: {decision_val}. Reason: {review_in.reason}"
    )
    db.add(history)

    # Promote to active placements and create resources if approved
    if decision_val == "approved":
        # Find or create Organization
        org = db.query(Organization).filter(Organization.name == req.proposed_company_name).first()
        if not org:
            org = Organization(
                name=req.proposed_company_name,
                address=req.proposed_company_address,
                industry=req.proposed_company_industry,
                contact_email=req.proposed_company_email,
                contact_phone=req.proposed_company_phone
            )
            db.add(org)
            db.commit()
            db.refresh(org)

        # Get supervisor profile
        confirm_rec = db.query(SupervisorConfirmation).filter(SupervisorConfirmation.placement_request_id == req.id).first()
        supervisor_id = None
        if confirm_rec:
            sv_profile = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == confirm_rec.supervisor_id).first()
            if sv_profile:
                # Associate supervisor to organization
                sv_profile.organization_id = org.id
                db.commit()
                supervisor_id = sv_profile.id

        # Create formal Placement
        final_start_date = req.start_date
        final_end_date = req.end_date
        final_duration_weeks = req.duration_weeks

        comparisons = db.query(FieldComparison).filter(FieldComparison.placement_request_id == req.id).all()
        for comp in comparisons:
            if comp.field_name == "start_date" and comp.supervisor_value:
                try:
                    final_start_date = datetime.datetime.strptime(comp.supervisor_value, "%Y-%m-%d").date()
                except ValueError:
                    pass
            elif comp.field_name == "end_date" and comp.supervisor_value:
                try:
                    final_end_date = datetime.datetime.strptime(comp.supervisor_value, "%Y-%m-%d").date()
                except ValueError:
                    pass
            elif comp.field_name == "duration_weeks" and comp.supervisor_value:
                try:
                    final_duration_weeks = int(comp.supervisor_value)
                except ValueError:
                    pass

        placement = Placement(
            student_id=req.student_id,
            organization_id=org.id,
            supervisor_id=supervisor_id,
            placement_request_id=req.id,
            start_date=final_start_date,
            end_date=final_end_date,
            duration_weeks=final_duration_weeks,
            status="approved"
        )
        db.add(placement)
        
        # Mark request as active
        req.status = "active"
        
        history_active = StatusHistory(
            placement_request_id=req.id,
            old_status="verified",
            new_status="active",
            changed_by=current_user.id,
            reason="Placement promoted to active state"
        )
        db.add(history_active)

    db.commit()
    return {"message": f"Placement request reviewed as {decision_val}"}

@router.get("/supervisor/queue", response_model=List[PlacementRequestResponse])
def get_supervisor_queue(
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    return db.query(PlacementRequest).filter(
        PlacementRequest.status.in_(["supervisor_confirmed", "under_coordinator_review", "awaiting_supervisor", "awaiting_hr_confirmation"]),
        PlacementRequest.proposed_supervisor_email == current_user.email
    ).all()

@router.get("/students", response_model=List[dict])
def list_students(
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    profiles = db.query(StudentProfile).all()
    out = []
    for p in profiles:
        out.append({
            "id": p.id,
            "matric_number": p.matric_number,
            "department": p.department,
            "level": p.level,
            "full_name": p.user.full_name,
            "email": p.user.email,
            "is_verified": p.is_verified
        })
    return out

@router.post("/students/{student_id}/verify", response_model=dict)
def verify_student(
    student_id: int,
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    p = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Student profile not found")
    p.is_verified = True
    db.commit()
    
    # Audit log
    create_audit_event(
        db, 
        current_user.id, 
        "VERIFY_STUDENT_IDENTITY", 
        "StudentProfile", 
        p.id, 
        {"student_name": p.user.full_name}
    )
    
    # Notification
    create_in_app_notify(
        db,
        p.user_id,
        "Identity Verified",
        "Your student identity verification was successfully approved by the Departmental Coordinator. You can now submit SIWES placement proposals.",
        "success"
    )
    
    return {"message": "Student identity verified successfully"}

@router.post("/evidence/{evidence_id}/review", response_model=dict)
def review_evidence(
    evidence_id: int,
    status: str = Form(...),  # accepted, rejected, unclear, expired
    review_notes: Optional[str] = Form(None),
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    ev = db.query(VerificationEvidence).filter(VerificationEvidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
        
    if status not in ["accepted", "rejected", "unclear", "expired"]:
        raise HTTPException(status_code=400, detail="Invalid evidence review status")
        
    ev.status = status
    ev.review_notes = review_notes
    db.commit()
    
    # Audit trail
    create_audit_event(
        db,
        current_user.id,
        "REVIEW_EVIDENCE",
        "VerificationEvidence",
        ev.id,
        {"status": status, "evidence_title": ev.title}
    )
    
    # Notify student
    student_user_id = ev.placement_request.student.user_id
    create_in_app_notify(
        db,
        student_user_id,
        "Evidence Document Reviewed",
        f"Your uploaded evidence document '{ev.title}' was reviewed as: {status.upper()}.",
        "info"
    )
    
    return {"message": "Evidence document reviewed successfully"}

@router.post("/request/{req_id}/appeal", response_model=dict)
def submit_appeal(
    req_id: int,
    appeal_description: str = Form(...),
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    req = db.query(PlacementRequest).filter(PlacementRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Placement request not found")
        
    if req.status != "rejected":
        raise HTTPException(status_code=400, detail="You can only appeal rejected requests")
        
    req.appeal_description = appeal_description
    req.is_disputed = True
    req.status = "under_coordinator_review"
    
    db.commit()
    
    # Audit trail
    create_audit_event(
        db,
        current_user.id,
        "SUBMIT_APPEAL",
        "PlacementRequest",
        req.id,
        {"reason": appeal_description}
    )
    
    return {"message": "Appeal submitted successfully. Re-entered review queue."}

@router.post("/hr/confirm/{token}", response_model=dict)
def hr_confirm_placement(
    token: str,
    db: Session = Depends(get_db)
):
    req = db.query(PlacementRequest).filter(PlacementRequest.hr_invitation_token == token).first()
    if not req:
        raise HTTPException(status_code=404, detail="HR confirmation token is invalid")
        
    req.hr_confirmed = True
    old_status = req.status
    req.status = "under_coordinator_review"
    
    history = StatusHistory(
        placement_request_id=req.id,
        old_status=old_status,
        new_status="under_coordinator_review",
        changed_by=None,
        reason="Company HR representative verified placement details via token"
    )
    db.add(history)
    db.commit()
    
    create_audit_event(
        db,
        None,
        "HR_CONFIRM_PLACEMENT",
        "PlacementRequest",
        req.id,
        {"hr_email": req.company_representative_email}
    )
    
    create_in_app_notify(
        db,
        req.student.user_id,
        "HR Placement Confirmed",
        f"The company representative for {req.proposed_company_name} confirmed your placement request details.",
        "success"
    )
    
    return {"message": "HR confirmation completed successfully."}

@router.post("/request/{req_id}/change-company", response_model=dict)
def change_company_request(
    req_id: int,
    reason: str = Form(...),
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    req = db.query(PlacementRequest).filter(PlacementRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Placement request not found")
        
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile or req.student_id != student_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    old_status = req.status
    req.status = "closed_for_transfer"
    
    # Deactivate active placements linked to this request
    placements = db.query(Placement).filter(Placement.placement_request_id == req.id).all()
    for p in placements:
        p.status = "inactive_transferred"
        
    history = StatusHistory(
        placement_request_id=req.id,
        old_status=old_status,
        new_status="closed_for_transfer",
        changed_by=current_user.id,
        reason=f"Student initiated transfer request. Reason: {reason}"
    )
    db.add(history)
    db.commit()
    
    create_audit_event(
        db,
        current_user.id,
        "TRANSFER_PLACEMENT_REQUEST",
        "PlacementRequest",
        req.id,
        {"reason": reason}
    )
    
    return {"message": "Placement closed. You may now submit a new placement request draft."}

@router.post("/placements/{placement_id}/replace-supervisor", response_model=dict)
def replace_supervisor(
    placement_id: int,
    new_supervisor_name: str = Form(...),
    new_supervisor_email: str = Form(...),
    new_supervisor_title: str = Form(...),
    reason: str = Form(...),
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")
        
    # Archive/Deactivate old supervisor relationship if wanted, or just update the supervisor profile
    # Let's create user for new supervisor
    existing_user = db.query(User).filter(User.email == new_supervisor_email).first()
    if existing_user:
        new_user = existing_user
    else:
        new_user = User(
            full_name=new_supervisor_name,
            email=new_supervisor_email,
            password_hash=get_password_hash("chrisland123"),  # default temp password
            role="supervisor",
            status="active"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
    sv_profile = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == new_user.id).first()
    if not sv_profile:
        sv_profile = IndustrySupervisor(
            user_id=new_user.id,
            organization_id=placement.organization_id,
            job_title=new_supervisor_title
        )
        db.add(sv_profile)
        db.commit()
        db.refresh(sv_profile)
        
    old_sv_name = placement.supervisor.user.full_name if placement.supervisor else "None"
    placement.supervisor_id = sv_profile.id
    db.commit()
    
    create_audit_event(
        db,
        current_user.id,
        "REPLACE_SUPERVISOR",
        "Placement",
        placement.id,
        {"old_supervisor": old_sv_name, "new_supervisor": new_supervisor_name, "reason": reason}
    )
    
    create_in_app_notify(
        db,
        placement.student.user_id,
        "Supervisor Reassigned",
        f"Your coordinator has replaced supervisor {old_sv_name} with {new_supervisor_name}. Reason: {reason}",
        "warning"
    )
    
    return {"message": "Supervisor replaced successfully and notification triggered."}

@router.get("/analytics", response_model=dict)
def get_coordinator_analytics(
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    # Stats
    total_students = db.query(StudentProfile).count()
    verified_students = db.query(StudentProfile).filter(StudentProfile.is_verified == True).count()
    
    total_reqs = db.query(PlacementRequest).count()
    pending_reqs = db.query(PlacementRequest).filter(PlacementRequest.status == "under_coordinator_review").count()
    verified_reqs = db.query(PlacementRequest).filter(PlacementRequest.status == "verified").count()
    active_reqs = db.query(PlacementRequest).filter(PlacementRequest.status == "active").count()
    rejected_reqs = db.query(PlacementRequest).filter(PlacementRequest.status == "rejected").count()
    disputed_reqs = db.query(PlacementRequest).filter(PlacementRequest.is_disputed == True).count()
    
    return {
        "total_students": total_students,
        "verified_students_count": verified_students,
        "total_requests": total_reqs,
        "pending_reviews": pending_reqs,
        "verified_placements": verified_reqs,
        "active_placements": active_reqs,
        "rejected_placements": rejected_reqs,
        "disputed_requests": disputed_reqs
    }

@router.get("/notifications", response_model=List[dict])
def list_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifs = db.query(Notification).filter(
        Notification.recipient_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(20).all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "read_at": n.read_at,
            "created_at": n.created_at
        } for n in notifs
    ]

@router.post("/notifications/{id}/read", response_model=dict)
def read_notification(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    n = db.query(Notification).filter(Notification.id == id, Notification.recipient_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Notification marked as read"}
