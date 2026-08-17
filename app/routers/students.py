from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile
from app.schemas.siwes_schemas import StudentProfileResponse, StudentProfileUpdate

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("/me", response_model=StudentProfileResponse)
def get_student_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a student"
        )
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    return profile

@router.patch("/me", response_model=StudentProfileResponse)
def update_student_profile(
    profile_in: StudentProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a student"
        )
        
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
        
    if profile_in.department is not None:
        profile.department = profile_in.department
    if profile_in.level is not None:
        profile.level = profile_in.level
    if profile_in.phone is not None:
        profile.phone = profile_in.phone
    if profile_in.address is not None:
        profile.address = profile_in.address
        
    # Generate cleaner matric if it is still temporary
    if profile.matric_number.startswith("TEMP-") and profile_in.phone:
        # A simple mock matric generator just to ensure it looks standard
        profile.matric_number = f"SIWES/{current_user.id:04d}"

    db.commit()
    db.refresh(profile)
    return profile
