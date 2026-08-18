from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime, date

# --- AUTH & USER SCHEMAS ---

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = Field(..., description="student, supervisor, coordinator, admin")
    matric_number: Optional[str] = None
    department: Optional[str] = None
    level: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

class StudentProfileCreate(BaseModel):
    matric_number: str
    department: str
    level: str
    phone: Optional[str] = None
    address: Optional[str] = None

class StudentProfileUpdate(BaseModel):
    department: Optional[str] = None
    level: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class StudentProfileResponse(BaseModel):
    id: int
    matric_number: str
    department: str
    level: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_verified: bool = False

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    status: str
    created_at: datetime
    student_profile: Optional[StudentProfileResponse] = None

    class Config:
        from_attributes = True

# --- ORGANIZATION & PLACEMENT SCHEMAS ---

class OrganizationCreate(BaseModel):
    name: str
    address: str
    industry: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None

class OrganizationResponse(BaseModel):
    id: int
    name: str
    address: str
    industry: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None

    class Config:
        from_attributes = True

class PlacementSubmit(BaseModel):
    organization_name: str
    organization_address: str
    organization_industry: Optional[str] = None
    organization_email: Optional[EmailStr] = None
    organization_phone: Optional[str] = None
    start_date: date
    end_date: date

class PlacementApproval(BaseModel):
    decision: str = Field(..., description="approved, rejected")
    supervisor_id: Optional[int] = None

class PlacementResponse(BaseModel):
    id: int
    student_id: int
    organization_id: Optional[int]
    supervisor_id: Optional[int]
    start_date: date
    end_date: date
    duration_weeks: int
    status: str
    organization: Optional[OrganizationResponse] = None

    class Config:
        from_attributes = True

# --- LOGBOOK & FEEDBACK SCHEMAS ---

class LogbookEntryCreate(BaseModel):
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

class LogbookEntryUpdate(BaseModel):
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
    id: int
    completeness_score: int
    suggestions: List[str]
    category: str
    repetition_flag: bool
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True

class EntryFeedbackResponse(BaseModel):
    id: int
    comment: str
    decision: str
    score: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class LogbookEntryResponse(BaseModel):
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
    tools_used: Optional[str]
    challenges: Optional[str]
    learning_outcome: Optional[str]
    status: str
    ai_reviews: List[AIReviewResponse] = []
    feedback: List[EntryFeedbackResponse] = []

    class Config:
        from_attributes = True

class FeedbackCreate(BaseModel):
    comment: str
    decision: str = Field(..., description="approved, rejected, revision_requested")
    score: Optional[int] = None

# --- ATTENDANCE & ASSESSMENT SCHEMAS ---

class AttendanceCreate(BaseModel):
    attendance_date: date
    status: str = Field(..., description="present, absent, excused")
    note: Optional[str] = None

class AttendanceResponse(BaseModel):
    id: int
    placement_id: int
    attendance_date: date
    status: str
    note: Optional[str]
    recorded_by: Optional[int]

    class Config:
        from_attributes = True

class AssessmentCreate(BaseModel):
    punctuality_score: int = Field(..., ge=0, le=20)
    technical_score: int = Field(..., ge=0, le=40)
    communication_score: int = Field(..., ge=0, le=20)
    professionalism_score: int = Field(..., ge=0, le=20)
    remarks: Optional[str] = None

class AssessmentResponse(BaseModel):
    id: int
    placement_id: int
    assessor_id: Optional[int]
    punctuality_score: int
    technical_score: int
    communication_score: int
    professionalism_score: int
    total_score: int
    remarks: Optional[str]
    status: str

    class Config:
        from_attributes = True

class PlacementRequestCreate(BaseModel):
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
    confirmation_statement: bool
    field_confirmations: dict
    field_corrections: dict

class EvidenceSubmit(BaseModel):
    evidence_type: str
    title: str
    issuer_name: Optional[str] = None
    issuer_contact: Optional[str] = None
    notes: Optional[str] = None

class VerificationReviewSubmit(BaseModel):
    decision: str
    reason: str

class FieldComparisonResponse(BaseModel):
    id: int
    field_name: str
    student_value: Optional[str]
    supervisor_value: Optional[str]
    match_status: str

    class Config:
        from_attributes = True

class VerificationEvidenceResponse(BaseModel):
    id: int
    evidence_type: str
    title: str
    file_url: str
    issuer_name: Optional[str]
    issuer_contact: Optional[str]
    notes: Optional[str]
    status: str
    review_notes: Optional[str] = None

    class Config:
        from_attributes = True

class StatusHistoryResponse(BaseModel):
    id: int
    old_status: Optional[str]
    new_status: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class PlacementRequestResponse(BaseModel):
    id: int
    student_id: int
    session_id: Optional[int]
    proposed_company_name: str
    proposed_company_address: str
    proposed_company_industry: Optional[str]
    proposed_company_email: Optional[str]
    proposed_company_phone: Optional[str]
    proposed_supervisor_name: str
    proposed_supervisor_job_title: str
    proposed_supervisor_email: str
    proposed_supervisor_phone: str
    proposed_supervisor_experience: Optional[int]
    proposed_supervisor_department: Optional[str]
    relationship_to_student: Optional[str]
    conflict_declaration: Optional[str]
    company_representative_name: Optional[str]
    company_representative_email: Optional[str]
    hr_invitation_token: Optional[str]
    hr_confirmed: bool
    start_date: date
    end_date: date
    duration_weeks: int
    how_obtained: Optional[str]
    proposed_duties: Optional[str]
    technical_areas: Optional[List[str]]
    expected_work: Optional[str]
    status: str
    appeal_description: Optional[str]
    is_disputed: bool
    submitted_at: Optional[datetime]
    created_at: datetime
    comparisons: List[FieldComparisonResponse] = []
    evidence: List[VerificationEvidenceResponse] = []
    history: List[StatusHistoryResponse] = []

    class Config:
        from_attributes = True

class InvitationResponse(BaseModel):
    id: int
    placement_request_id: int
    email: str
    token_hash: str
    expires_at: datetime
    status: str
    student_name: str
    proposed_company_name: str

    class Config:
        from_attributes = True

class AcademicSessionCreate(BaseModel):
    name: str
    registration_start: date
    registration_end: date
    placement_deadline: date
    assessment_deadline: date

class AcademicSessionResponse(BaseModel):
    id: int
    name: str
    registration_start: date
    registration_end: date
    placement_deadline: date
    assessment_deadline: date
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
