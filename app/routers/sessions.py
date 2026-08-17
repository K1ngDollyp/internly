from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import RoleChecker
from app.models.siwes import User, AcademicSession
from app.schemas.siwes_schemas import AcademicSessionCreate, AcademicSessionResponse
from typing import List

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("", response_model=AcademicSessionResponse)
def create_session(
    sess_in: AcademicSessionCreate,
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    existing = db.query(AcademicSession).filter(AcademicSession.name == sess_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Academic session with this name already exists")
    
    new_sess = AcademicSession(
        name=sess_in.name,
        registration_start=sess_in.registration_start,
        registration_end=sess_in.registration_end,
        placement_deadline=sess_in.placement_deadline,
        assessment_deadline=sess_in.assessment_deadline,
        status="active"
    )
    db.add(new_sess)
    db.commit()
    db.refresh(new_sess)
    return new_sess

@router.get("", response_model=List[AcademicSessionResponse])
def list_sessions(
    current_user: User = Depends(RoleChecker(["coordinator", "student", "supervisor"])),
    db: Session = Depends(get_db)
):
    return db.query(AcademicSession).order_by(AcademicSession.id.desc()).all()

@router.post("/{sess_id}/activate", response_model=AcademicSessionResponse)
def activate_session(
    sess_id: int,
    current_user: User = Depends(RoleChecker(["coordinator"])),
    db: Session = Depends(get_db)
):
    sess = db.query(AcademicSession).filter(AcademicSession.id == sess_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Academic session not found")
        
    # Archive all others
    db.query(AcademicSession).filter(AcademicSession.id != sess_id).update({"status": "archived"})
    sess.status = "active"
    db.commit()
    db.refresh(sess)
    return sess
