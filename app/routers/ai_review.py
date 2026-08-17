from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile, Placement, LogbookEntry, AIReview
from app.schemas.siwes_schemas import AIReviewResponse
from app.services.ai_service import LogbookAIModel
from typing import List

router = APIRouter(prefix="/logbook-entries", tags=["AI Logbook Quality Assistant"])

@router.post("/{entry_id}/ai-review", response_model=AIReviewResponse)
def evaluate_logbook_quality(
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
        
    # Get previous logbook entries for the placement to run similarity/repetition checks
    previous_entries = db.query(LogbookEntry.activities).filter(
        LogbookEntry.placement_id == entry.placement_id,
        LogbookEntry.id != entry.id
    ).all()
    prev_activities_list = [p[0] for p in previous_entries if p[0]]

    # Run local AI model
    analysis = LogbookAIModel.evaluate_entry(
        activities=entry.activities,
        tools_used=entry.tools_used,
        challenges=entry.challenges,
        learning_outcome=entry.learning_outcome,
        previous_entries=prev_activities_list
    )

    # Save to Database
    ai_review = AIReview(
        entry_id=entry.id,
        completeness_score=analysis["completenessScore"],
        suggestions=analysis["suggestions"],
        category=analysis["category"],
        repetition_flag=analysis["repetitionFlag"],
        model_version="Internly-LocalAI-v1.0"
    )
    db.add(ai_review)
    db.commit()
    db.refresh(ai_review)

    return ai_review
