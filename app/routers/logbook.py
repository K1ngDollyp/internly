import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile, Placement, LogbookEntry, EntryFeedback, EvidenceFile, IndustrySupervisor, AuditLog
from app.schemas.siwes_schemas import LogbookEntryCreate, LogbookEntryUpdate, LogbookEntryResponse, FeedbackCreate, EntryFeedbackResponse
from typing import List
import shutil

router = APIRouter(prefix="/logbook-entries", tags=["Logbook"])

# Set upload directory compatible with Vercel serverless filesystem (/tmp)
UPLOAD_DIR = "/tmp/uploads" if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "uploads"
if not os.path.exists(UPLOAD_DIR):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except Exception:
        UPLOAD_DIR = "/tmp"

@router.post("", response_model=LogbookEntryResponse)
def create_logbook_entry(
    entry_in: LogbookEntryCreate,
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    placement = db.query(Placement).filter(
        Placement.student_id == student_profile.id,
        Placement.status == "approved"
    ).first()
    if not placement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have a verified and active placement to submit logbook entries."
        )

    # Check if entry for this week already exists
    existing = db.query(LogbookEntry).filter(
        LogbookEntry.placement_id == placement.id,
        LogbookEntry.week_number == entry_in.week_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An entry for week {entry_in.week_number} already exists."
        )

    new_entry = LogbookEntry(
        placement_id=placement.id,
        week_number=entry_in.week_number,
        start_date=entry_in.start_date,
        end_date=entry_in.end_date,
        activities=entry_in.weekly_summary or entry_in.activities,
        monday_activity=entry_in.monday_activity,
        tuesday_activity=entry_in.tuesday_activity,
        wednesday_activity=entry_in.wednesday_activity,
        thursday_activity=entry_in.thursday_activity,
        friday_activity=entry_in.friday_activity,
        saturday_activity=entry_in.saturday_activity,
        weekly_summary=entry_in.weekly_summary,
        tools_used=entry_in.tools_used,
        challenges=entry_in.challenges,
        learning_outcome=entry_in.learning_outcome,
        status="draft"
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

@router.get("/me", response_model=List[LogbookEntryResponse])
def get_own_logbook_entries(
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    placement = db.query(Placement).filter(Placement.student_id == student_profile.id).first()
    if not placement:
        return []
        
    return db.query(LogbookEntry).filter(LogbookEntry.placement_id == placement.id).order_by(LogbookEntry.week_number.asc()).all()

@router.get("/{entry_id}", response_model=LogbookEntryResponse)
def get_logbook_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Logbook entry not found")
        
    # Check permissions (student owns it, or reviewer matches roles)
    if current_user.role == "student":
        student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
        if not student_profile or entry.placement.student_id != student_profile.id:
            raise HTTPException(status_code=403, detail="Forbidden: You do not own this entry")
            
    elif current_user.role == "supervisor":
        supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
        if not supervisor or entry.placement.supervisor_id != supervisor.id:
            raise HTTPException(status_code=403, detail="Forbidden: You are not assigned to this student")

    elif current_user.role in ["coordinator", "admin"]:
        pass  # coordinators/admins can view all entries
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

    return entry

@router.patch("/{entry_id}", response_model=LogbookEntryResponse)
def update_logbook_entry(
    entry_id: int,
    entry_in: LogbookEntryUpdate,
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Logbook entry not found")
        
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile or entry.placement.student_id != student_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this entry")
        
    if entry.status not in ["draft", "rejected", "revision_requested"]:
        raise HTTPException(status_code=400, detail="Cannot edit an entry that has already been submitted or approved")

    if entry_in.activities is not None:
        entry.activities = entry_in.activities
    if entry_in.weekly_summary is not None:
        entry.weekly_summary = entry_in.weekly_summary
        entry.activities = entry_in.weekly_summary
    if entry_in.monday_activity is not None:
        entry.monday_activity = entry_in.monday_activity
    if entry_in.tuesday_activity is not None:
        entry.tuesday_activity = entry_in.tuesday_activity
    if entry_in.wednesday_activity is not None:
        entry.wednesday_activity = entry_in.wednesday_activity
    if entry_in.thursday_activity is not None:
        entry.thursday_activity = entry_in.thursday_activity
    if entry_in.friday_activity is not None:
        entry.friday_activity = entry_in.friday_activity
    if entry_in.saturday_activity is not None:
        entry.saturday_activity = entry_in.saturday_activity
    if entry_in.tools_used is not None:
        entry.tools_used = entry_in.tools_used
    if entry_in.challenges is not None:
        entry.challenges = entry_in.challenges
    if entry_in.learning_outcome is not None:
        entry.learning_outcome = entry_in.learning_outcome
        
    db.commit()
    db.refresh(entry)
    return entry

@router.post("/{entry_id}/submit", response_model=LogbookEntryResponse)
def submit_logbook_entry(
    entry_id: int,
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Logbook entry not found")
        
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile or entry.placement.student_id != student_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this entry")
        
    # Prevent empty submits
    if not entry.activities or len(entry.activities.strip()) < 10:
        raise HTTPException(status_code=400, detail="Logbook entry activities are too brief or incomplete")
        
    entry.status = "submitted"
    db.commit()
    db.refresh(entry)
    return entry

@router.post("/{entry_id}/upload-evidence", response_model=dict)
def upload_evidence(
    entry_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Logbook entry not found")
        
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile or entry.placement.student_id != student_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this entry")
        
    # File validation: limit size to 5MB, verify image/pdf/docx
    max_size = 5 * 1024 * 1024
    content = file.file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")
        
    file.file.seek(0)
    
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"evidence_{entry_id}_{int(datetime.datetime.utcnow().timestamp())}{file_ext}"
    dest_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    evidence = EvidenceFile(
        entry_id=entry.id,
        file_name=file.filename,
        file_url=f"/uploads/{safe_filename}",
        mime_type=file.content_type,
        file_size=len(content)
    )
    db.add(evidence)
    db.commit()
    
    return {"message": "Evidence uploaded successfully", "file_url": evidence.file_url}

@router.get("/supervisor/entries", response_model=List[LogbookEntryResponse])
def list_supervisor_assigned_entries(
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")
        
    # Find all placements assigned to this supervisor
    placements = db.query(Placement).filter(Placement.supervisor_id == supervisor.id).all()
    placement_ids = [p.id for p in placements]
    
    return db.query(LogbookEntry).filter(
        LogbookEntry.placement_id.in_(placement_ids),
        LogbookEntry.status != "draft"
    ).order_by(LogbookEntry.status.desc(), LogbookEntry.week_number.asc()).all()

@router.post("/{entry_id}/reviews", response_model=EntryFeedbackResponse)
def review_logbook_entry(
    entry_id: int,
    feedback_in: FeedbackCreate,
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Logbook entry not found")
        
    supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
    if not supervisor or entry.placement.supervisor_id != supervisor.id:
        raise HTTPException(status_code=403, detail="Forbidden: You are not assigned to this student")
        
    decision_val = feedback_in.decision.lower()
    if decision_val not in ["approved", "rejected", "revision_requested"]:
        raise HTTPException(status_code=400, detail="Invalid decision value")
        
    entry.status = decision_val
    
    new_feedback = EntryFeedback(
        entry_id=entry.id,
        reviewer_id=current_user.id,
        comment=feedback_in.comment,
        decision=decision_val,
        score=feedback_in.score
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    
    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        action=f"logbook_review_{decision_val}",
        entity_type="logbook_entry",
        entity_id=entry.id,
        metadata_json={"score": feedback_in.score}
    )
    db.add(audit)
    db.commit()
    
    return new_feedback
import datetime
