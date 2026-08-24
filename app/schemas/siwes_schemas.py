"""
SIWES System API Data Schemas (Pydantic V2)
---------------------------------------------
This module defines all request, response, and validation Data Transfer Objects (DTOs)
used across the FastAPI endpoints. Each schema validates incoming HTTP JSON payloads
and formats outbound database model objects cleanly.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime, date

# =============================================================================
# 1. AUTHENTICATION & USER SCHEMAS
# =============================================================================

class UserRegister(BaseModel):
    """Schema for new user registration."""
    full_name: str = Field(..., json_schema_extra={"example": "Oluwaseun Adeleke"}, description="Full name of the user")
    email: EmailStr = Field(..., json_schema_extra={"example": "student@university.edu.ng"}, description="Official university or organizational email")
    password: str = Field(..., min_length=3, description="Password for account access")
    role: str = Field(..., description="System role: student, supervisor, coordinator, admin")
    matric_number: Optional[str] = Field(None, description="Required if role is student (e.g., RUN/CSC/20/8901)")
    department: Optional[str] = Field(None, description="Academic department (e.g., Computer Science)")
    level: Optional[str] = Field(None, description="Academic level (e.g., 300, 400)")


class UserLogin(BaseModel):
    """Schema for OAuth2 / Password authentication requests."""
    email: EmailStr
    password: str

class Token(BaseModel):
    """JWT Access Token response structure."""
    access_token: str
    token_type: str = "bearer"
    role: str

class UserProfileUpdate(BaseModel):
    """Schema for updating basic user account information."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

class StudentProfileCreate(BaseModel):
    """Schema for initializing a student's SIWES profile."""
    matric_number: str
    department: str
    level: str
    phone: Optional[str] = None
    address: Optional[str] = None

class StudentProfileUpdate(BaseModel):
    """Schema for updating an existing student profile."""
    department: Optional[str] = None
    level: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class StudentProfileResponse(BaseModel):
    """Outbound representation of a student's profile."""
    id: int
    matric_number: str
    department: str
    level: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_verified: bool = False

    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    """Public account response object containing optional nested student profile."""
    id: int
    full_name: str
    email: EmailStr
    role: str
    status: str
    created_at: datetime
    student_profile: Optional[StudentProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 2. ORGANIZATION & PLACEMENT SCHEMAS
# =============================================================================

class OrganizationCreate(BaseModel):
    """Schema for registering an IT/Engineering host organization."""
    name: str
    address: str
    industry: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None

class OrganizationResponse(BaseModel):
    """Public representation of an approved host organization."""
    id: int
    name: str
    address: str
    industry: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PlacementSubmit(BaseModel):
    """Payload for submitting SIWES placement details."""
    organization_name: str
    organization_address: str
    organization_industry: Optional[str] = None
    organization_email: Optional[EmailStr] = None
    organization_phone: Optional[str] = None
    start_date: date
    end_date: date

class PlacementApproval(BaseModel):
    """Coordinator decision payload for placement approval."""
    decision: str = Field(..., description="approved, rejected")
    supervisor_id: Optional[int] = None

class PlacementResponse(BaseModel):
    """Outbound representation of an active SIWES placement."""
    id: int
    student_id: int
    organization_id: Optional[int]
    supervisor_id: Optional[int]
    start_date: date
    end_date: date
    duration_weeks: int
    status: str
    organization: Optional[OrganizationResponse] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 3. LOGBOOK, AI REVIEW & FEEDBACK SCHEMAS
# =============================================================================

class LogbookEntryCreate(BaseModel):
    """Payload for submitting a weekly SIWES logbook entry."""
    week_number: int
    start_date: date
    end_date: date
    activities: str = Field(..., min_length=20, description="Overall summary of activities performed")
    monday_activity: Optional[str] = None
    tuesday_activity: Optional[str] = None
    wednesday_activity: Optional[str] = None
    thursday_activity: Optional[str] = None
    friday_activity: Optional[str] = None
    saturday_activity: Optional[str] = None
    weekly_summary: Optional[str] = None
    tools_used: Optional[str] = Field(None, description="Software tools, hardware, or frameworks used")
    challenges: Optional[str] = Field(None, description="Technical challenges encountered during the week")
    learning_outcome: Optional[str] = Field(None, description="Key technical skills or concepts acquired")

class LogbookEntryUpdate(BaseModel):
    """Payload for modifying a draft or revision-requested logbook entry."""
    activities: Optional[str] = None
    monday_activity: Optional[str] = None
    tuesday_activity: Optional[str] = None
    wednesday_activity: Optional[str] = None
    thursday_activity: Optional[str] = None
    friday_activity: Optional[str] = None
    saturday_activity: Optional[str] = None
    weekly_summary: Optional[str] = None
    tools_used: Optional[str] = None
    challenges: Optional[str] = None
    learning_outcome: Optional[str] = None

class AIReviewResponse(BaseModel):
    """Outbound evaluation response generated by the local AI Logbook Quality Evaluator."""
    id: int
    completeness_score: int
    suggestions: List[str]
    category: str
    repetition_flag: bool
    model_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EntryFeedbackResponse(BaseModel):
    """Feedback and scoring provided by the industry supervisor."""
    id: int
    comment: str
    decision: str
    score: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LogbookEntryResponse(BaseModel):
    """Complete logbook entry response including nested AI reviews and supervisor feedback."""
    id: int
    placement_id: int
    week_number: int
    start_date: date
    end_date: date
    activities: str
    monday_activity: Optional[str] = None
    tuesday_activity: Optional[str] = None
    wednesday_activity: Optional[str] = None
    thursday_activity: Optional[str] = None
    friday_activity: Optional[str] = None
    saturday_activity: Optional[str] = None
    weekly_summary: Optional[str] = None
    tools_used: Optional[str] = None
    challenges: Optional[str] = None
    learning_outcome: Optional[str] = None
    status: str
    ai_reviews: List[AIReviewResponse] = []
    feedback: List[EntryFeedbackResponse] = []

    model_config = ConfigDict(from_attributes=True)

class FeedbackCreate(BaseModel):
    """Industry supervisor feedback submission payload."""
    comment: str
    decision: str = Field(..., description="approved, rejected, revision_requested")
    score: Optional[int] = Field(None, ge=0, le=100)


# =============================================================================
# 4. ATTENDANCE & ASSESSMENT SCHEMAS
# =============================================================================

class AttendanceCreate(BaseModel):
    """Single attendance record entry."""
    attendance_date: date
    status: str = Field(..., description="present, absent, excused")
    note: Optional[str] = None

class AttendanceResponse(BaseModel):
    """Outbound representation of an attendance record."""
    id: int
    placement_id: int
    attendance_date: date
    status: str
    note: Optional[str] = None
    recorded_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class AssessmentCreate(BaseModel):
    """Industry supervisor final assessment scoring form (Total = 100)."""
    punctuality_score: int = Field(..., ge=0, le=20, description="Punctuality and attendance score (Max 20)")
    technical_score: int = Field(..., ge=0, le=40, description="Technical competence & skill acquisition (Max 40)")
    communication_score: int = Field(..., ge=0, le=20, description="Communication & team relationship (Max 20)")
    professionalism_score: int = Field(..., ge=0, le=20, description="Workplace ethics & professionalism (Max 20)")
    remarks: Optional[str] = None

class AssessmentResponse(BaseModel):
    """Outbound finalized assessment record."""
    id: int
    placement_id: int
    assessor_id: Optional[int] = None
    punctuality_score: int
    technical_score: int
    communication_score: int
    professionalism_score: int
    total_score: int
    remarks: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 5. VERIFICATION & PLACEMENT REQUEST SCHEMAS
# =============================================================================

class PlacementRequestCreate(BaseModel):
    """Initial placement verification request submitted by student."""
    proposed_company_name: str
    proposed_company_address: str
    proposed_company_industry: Optional[str] = None
    proposed_company_email: Optional[EmailStr] = None
    proposed_company_phone: Optional[str] = None
    proposed_supervisor_name: str
    proposed_supervisor_job_title: str
    proposed_supervisor_email: EmailStr
    proposed_supervisor_phone: str
    proposed_supervisor_experience: Optional[int] = None
    proposed_supervisor_department: Optional[str] = None
    relationship_to_student: Optional[str] = None
    conflict_declaration: Optional[str] = None
    company_representative_name: Optional[str] = None
    company_representative_email: Optional[EmailStr] = None
    start_date: date
    end_date: date
    duration_weeks: Optional[int] = 24
    how_obtained: Optional[str] = None
    proposed_duties: Optional[str] = None
    technical_areas: Optional[List[str]] = None
    expected_work: Optional[str] = None
    session_id: Optional[int] = None

class PlacementRequestUpdate(BaseModel):
    """Payload for student to edit placement request prior to supervisor confirmation."""
    proposed_company_name: Optional[str] = None
    proposed_company_address: Optional[str] = None
    proposed_company_industry: Optional[str] = None
    proposed_company_email: Optional[EmailStr] = None
    proposed_company_phone: Optional[str] = None
    proposed_supervisor_name: Optional[str] = None
    proposed_supervisor_job_title: Optional[str] = None
    proposed_supervisor_email: Optional[EmailStr] = None
    proposed_supervisor_phone: Optional[str] = None
    proposed_supervisor_experience: Optional[int] = None
    proposed_supervisor_department: Optional[str] = None
    relationship_to_student: Optional[str] = None
    conflict_declaration: Optional[str] = None
    company_representative_name: Optional[str] = None
    company_representative_email: Optional[EmailStr] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_weeks: Optional[int] = None
    how_obtained: Optional[str] = None
    proposed_duties: Optional[str] = None
    technical_areas: Optional[List[str]] = None
    expected_work: Optional[str] = None
    session_id: Optional[int] = None

class SupervisorConfirmationSubmit(BaseModel):
    """Field-by-field verification payload submitted by supervisor via invitation link."""
    confirmation_statement: bool
    field_confirmations: dict
    field_corrections: dict

class EvidenceSubmit(BaseModel):
    """Supporting document metadata (e.g. Acceptance Letter PDF)."""
    evidence_type: str
    title: str
    issuer_name: Optional[str] = None
    issuer_contact: Optional[str] = None
    notes: Optional[str] = None

class VerificationReviewSubmit(BaseModel):
    """Departmental Coordinator final approval or rejection submission."""
    decision: str = Field(..., description="approved, rejected, revision_requested")
    reason: str

class FieldComparisonResponse(BaseModel):
    """Diff result comparing student-submitted values against supervisor-confirmed values."""
    id: int
    field_name: str
    student_value: Optional[str] = None
    supervisor_value: Optional[str] = None
    match_status: str

    model_config = ConfigDict(from_attributes=True)

class VerificationEvidenceResponse(BaseModel):
    """Outbound uploaded evidence file metadata."""
    id: int
    evidence_type: str
    title: str
    file_url: str
    issuer_name: Optional[str] = None
    issuer_contact: Optional[str] = None
    notes: Optional[str] = None
    status: str
    review_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class StatusHistoryResponse(BaseModel):
    """Audit record tracking placement verification status changes."""
    id: int
    old_status: Optional[str] = None
    new_status: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PlacementRequestResponse(BaseModel):
    """Complete placement verification request with comparisons, evidence, and audit history."""
    id: int
    student_id: int
    session_id: Optional[int] = None
    proposed_company_name: str
    proposed_company_address: str
    proposed_company_industry: Optional[str] = None
    proposed_company_email: Optional[str] = None
    proposed_company_phone: Optional[str] = None
    proposed_supervisor_name: str
    proposed_supervisor_job_title: str
    proposed_supervisor_email: str
    proposed_supervisor_phone: str
    proposed_supervisor_experience: Optional[int] = None
    proposed_supervisor_department: Optional[str] = None
    relationship_to_student: Optional[str] = None
    conflict_declaration: Optional[str] = None
    company_representative_name: Optional[str] = None
    company_representative_email: Optional[str] = None
    hr_invitation_token: Optional[str] = None
    hr_confirmed: bool
    start_date: date
    end_date: date
    duration_weeks: int
    how_obtained: Optional[str] = None
    proposed_duties: Optional[str] = None
    technical_areas: Optional[List[str]] = None
    expected_work: Optional[str] = None
    status: str
    appeal_description: Optional[str] = None
    is_disputed: bool = False
    submitted_at: Optional[datetime] = None
    created_at: datetime
    comparisons: List[FieldComparisonResponse] = []
    evidence: List[VerificationEvidenceResponse] = []
    history: List[StatusHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)

class InvitationResponse(BaseModel):
    """Tokenized invitation details returned for supervisor confirmation page."""
    id: int
    placement_request_id: int
    email: str
    token_hash: str
    expires_at: datetime
    status: str
    student_name: str
    proposed_company_name: str

    model_config = ConfigDict(from_attributes=True)

class AcademicSessionCreate(BaseModel):
    """Payload for creating a new SIWES academic session."""
    name: str = Field(..., json_schema_extra={"example": "2026 SIWES Programme"})
    registration_start: date
    registration_end: date
    placement_deadline: date
    assessment_deadline: date

class AcademicSessionResponse(BaseModel):
    """Outbound active academic session metadata."""
    id: int
    name: str
    registration_start: date
    registration_end: date
    placement_deadline: date
    assessment_deadline: date
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

