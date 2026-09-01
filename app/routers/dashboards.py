from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from typing import Dict, Any, List
from app.models.siwes import User, StudentProfile, Placement, LogbookEntry, Assessment, IndustrySupervisor, Organization, AuditLog, Notification

router = APIRouter(prefix="/dashboard", tags=["Dashboards"])

@router.get("/audit-logs", response_model=List[dict])
def get_audit_logs(
    current_user: User = Depends(RoleChecker(["coordinator", "admin"])),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    result = []
    for log in logs:
        actor = db.query(User).filter(User.id == log.actor_id).first() if log.actor_id else None
        result.append({
            "id": log.id,
            "timestamp": log.created_at.isoformat() if log.created_at else "",
            "actor_name": actor.full_name if actor else "System",
            "actor_role": actor.role if actor else "system",
            "action": log.action,
            "entity_type": log.entity_type or "-",
            "entity_id": log.entity_id or "-",
            "details": log.metadata_json or {}
        })
    return result

@router.get("/notifications", response_model=List[dict])
def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification).filter(
        Notification.recipient_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(20).all()
    
    return [{
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "type": n.type,
        "created_at": n.created_at.isoformat() if n.created_at else "",
        "is_read": n.read_at is not None
    } for n in notifications]

@router.get("/student", response_model=dict)
def get_student_dashboard(
    current_user: User = Depends(RoleChecker(["student"])),
    db: Session = Depends(get_db)
):
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    placement = db.query(Placement).filter(Placement.student_id == student_profile.id).order_by(Placement.id.desc()).first()
    
    # Calculate stats
    total_weeks = 24
    completed_weeks = 0
    pending_weeks = 0
    placement_status = "unregistered"
    placement_details = None
    
    if placement:
        placement_status = placement.status
        total_weeks = placement.duration_weeks
        placement_details = {
            "id": placement.id,
            "organization_name": placement.organization.name if placement.organization else "N/A",
            "start_date": placement.start_date.isoformat(),
            "end_date": placement.end_date.isoformat(),
            "supervisor_name": placement.supervisor.user.full_name if (placement.supervisor and placement.supervisor.user) else "Unassigned"
        }
        
        # Weeks counts
        completed_weeks = db.query(func.count(LogbookEntry.id)).filter(
            LogbookEntry.placement_id == placement.id,
            LogbookEntry.status == "approved"
        ).scalar() or 0
        
        pending_weeks = db.query(func.count(LogbookEntry.id)).filter(
            LogbookEntry.placement_id == placement.id,
            LogbookEntry.status == "submitted"
        ).scalar() or 0

    return {
        "placement_status": placement_status,
        "placement_details": placement_details,
        "completed_weeks": completed_weeks,
        "pending_weeks": pending_weeks,
        "total_weeks": total_weeks,
        "progress_percentage": round((completed_weeks / total_weeks) * 100, 1) if total_weeks > 0 else 0
    }

@router.get("/supervisor", response_model=dict)
def get_supervisor_dashboard(
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")
        
    # Get assigned placements
    placements = db.query(Placement).filter(Placement.supervisor_id == supervisor.id).all()
    placement_ids = [p.id for p in placements]
    
    # Calculate counts
    assigned_students_count = len(placements)
    
    pending_reviews_count = db.query(func.count(LogbookEntry.id)).filter(
        LogbookEntry.placement_id.in_(placement_ids) if placement_ids else False,
        LogbookEntry.status == "submitted"
    ).scalar() or 0
    
    # Get students list details
    students_list = []
    for p in placements:
        latest_entry = db.query(LogbookEntry).filter(LogbookEntry.placement_id == p.id).order_by(LogbookEntry.week_number.desc()).first()
        students_list.append({
            "placement_id": p.id,
            "student_name": p.student.user.full_name,
            "matric_number": p.student.matric_number,
            "department": p.student.department,
            "completed_weeks": db.query(func.count(LogbookEntry.id)).filter(LogbookEntry.placement_id == p.id, LogbookEntry.status == "approved").scalar(),
            "latest_activity": latest_entry.activities[:100] + "..." if (latest_entry and latest_entry.activities) else "No entries yet",
            "status": p.status
        })

    return {
        "assigned_students_count": assigned_students_count,
        "pending_reviews_count": pending_reviews_count,
        "students": students_list
    }

@router.get("/coordinator", response_model=dict)
def get_coordinator_dashboard(
    current_user: User = Depends(RoleChecker(["coordinator", "admin"])),
    db: Session = Depends(get_db)
):
    total_students = db.query(func.count(StudentProfile.id)).scalar() or 0
    total_placements = db.query(func.count(Placement.id)).scalar() or 0
    approved_placements = db.query(func.count(Placement.id)).filter(Placement.status == "approved").scalar() or 0
    pending_placements = db.query(func.count(Placement.id)).filter(Placement.status == "pending").scalar() or 0
    
    # Overdue entries: Active placements with no entries in the last 7 days (or simply placements with few weeks completed)
    placements = db.query(Placement).filter(Placement.status == "approved").all()
    students_at_risk = []
    
    for p in placements:
        completed = db.query(func.count(LogbookEntry.id)).filter(
            LogbookEntry.placement_id == p.id,
            LogbookEntry.status == "approved"
        ).scalar() or 0
        
        # If student has logged less than expected weeks (assuming 1 log per week from start)
        if completed < 2:  # flagging students with low activity for demonstration
            students_at_risk.append({
                "student_name": p.student.user.full_name,
                "matric_number": p.student.matric_number,
                "organization": p.organization.name if p.organization else "N/A",
                "completed_weeks": completed
            })

    return {
        "total_students": total_students,
        "total_placements": total_placements,
        "approved_placements": approved_placements,
        "pending_placements": pending_placements,
        "placement_rate_pct": round((approved_placements / total_students) * 100, 1) if total_students > 0 else 0,
        "students_at_risk": students_at_risk
    }
