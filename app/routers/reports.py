import os
import datetime
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile, Placement, FinalReport, LogbookEntry, Assessment, AuditLog
from typing import List

router = APIRouter(prefix="/reports", tags=["Reports"])

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("", response_model=dict)
def submit_final_report(
    file: UploadFile = File(...),
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
            detail="You must have an approved placement to upload your final report."
        )

    # Validate file size (max 10MB) and type
    max_size = 10 * 1024 * 1024
    content = file.file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    file.file.seek(0)

    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"report_{placement.id}_{int(datetime.datetime.utcnow().timestamp())}{file_ext}"
    dest_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    report = FinalReport(
        placement_id=placement.id,
        file_url=f"/uploads/{safe_filename}",
        status="submitted"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        action="submit_final_report",
        entity_type="final_report",
        entity_id=report.id,
        metadata_json={"filename": file.filename}
    )
    db.add(audit)
    db.commit()

    return {"message": "Final report submitted successfully", "file_url": report.file_url, "id": report.id}

@router.get("/progress", response_model=dict)
def generate_progress_report(
    placement_id: int,
    current_user: User = Depends(RoleChecker(["coordinator", "admin", "supervisor"])),
    db: Session = Depends(get_db)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")
        
    # Gather logs and assessments
    entries = db.query(LogbookEntry).filter(LogbookEntry.placement_id == placement_id).all()
    assessment = db.query(Assessment).filter(Assessment.placement_id == placement_id).first()
    
    entries_summary = []
    for e in entries:
        entries_summary.append({
            "week_number": e.week_number,
            "activities": e.activities,
            "status": e.status,
            "score": e.feedback[0].score if (e.feedback and e.feedback[0].score) else None
        })

    return {
        "student_name": placement.student.user.full_name,
        "matric_number": placement.student.matric_number,
        "department": placement.student.department,
        "organization": placement.organization.name if placement.organization else "N/A",
        "start_date": placement.start_date.isoformat(),
        "end_date": placement.end_date.isoformat(),
        "status": placement.status,
        "total_weeks_logged": len(entries),
        "logbook_entries": entries_summary,
        "assessment": {
            "punctuality_score": assessment.punctuality_score,
            "technical_score": assessment.technical_score,
            "communication_score": assessment.communication_score,
            "professionalism_score": assessment.professionalism_score,
            "total_score": assessment.total_score,
            "remarks": assessment.remarks,
            "status": assessment.status
        } if assessment else None
    }

@router.get("/{report_id}", response_model=dict)
def get_report_status(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(FinalReport).filter(FinalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    # Check permissions
    if current_user.role == "student":
        student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
        if not student_profile or report.placement.student_id != student_profile.id:
            raise HTTPException(status_code=403, detail="Forbidden: Access Denied")
            
    return {
        "id": report.id,
        "file_url": report.file_url,
        "submitted_at": report.submitted_at.isoformat(),
        "status": report.status,
        "reviewer_comment": report.reviewer_comment
    }
