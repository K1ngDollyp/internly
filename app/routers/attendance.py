from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile, Placement, Attendance, IndustrySupervisor
from app.schemas.siwes_schemas import AttendanceCreate, AttendanceResponse
from typing import List

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.post("", response_model=AttendanceResponse)
def record_attendance(
    attendance_in: AttendanceCreate,
    placement_id: int,
    current_user: User = Depends(RoleChecker(["supervisor"])),
    db: Session = Depends(get_db)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")
        
    supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
    if not supervisor or placement.supervisor_id != supervisor.id:
        raise HTTPException(status_code=403, detail="Forbidden: You are not the supervisor of this student")
        
    # Check if attendance for this date is already recorded
    existing = db.query(Attendance).filter(
        Attendance.placement_id == placement_id,
        Attendance.attendance_date == attendance_in.attendance_date
    ).first()
    
    if existing:
        existing.status = attendance_in.status
        existing.note = attendance_in.note
        existing.recorded_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing

    new_att = Attendance(
        placement_id=placement_id,
        attendance_date=attendance_in.attendance_date,
        status=attendance_in.status,
        note=attendance_in.note,
        recorded_by=current_user.id
    )
    db.add(new_att)
    db.commit()
    db.refresh(new_att)
    return new_att

@router.get("/placement/{placement_id}", response_model=List[AttendanceResponse])
def get_placement_attendance(
    placement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")
        
    # Check permission
    if current_user.role == "student":
        student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
        if not student_profile or placement.student_id != student_profile.id:
            raise HTTPException(status_code=403, detail="Forbidden: Access Denied")
            
    elif current_user.role == "supervisor":
        supervisor = db.query(IndustrySupervisor).filter(IndustrySupervisor.user_id == current_user.id).first()
        if not supervisor or placement.supervisor_id != supervisor.id:
            raise HTTPException(status_code=403, detail="Forbidden: Access Denied")
            
    return db.query(Attendance).filter(Attendance.placement_id == placement_id).order_by(Attendance.attendance_date.desc()).all()
