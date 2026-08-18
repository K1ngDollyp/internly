import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Date, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # student, supervisor, coordinator, admin
    status = Column(String, default="active")  # active, suspended
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    student_profile = relationship("StudentProfile", uselist=False, back_populates="user")
    supervisor_profile = relationship("IndustrySupervisor", uselist=False, back_populates="user")

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    matric_number = Column(String, unique=True, index=True, nullable=False)
    department = Column(String, nullable=False)
    level = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)

    user = relationship("User", back_populates="student_profile")
    placements = relationship("Placement", back_populates="student")

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    address = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    placements = relationship("Placement", back_populates="organization")
    supervisors = relationship("IndustrySupervisor", back_populates="organization")

class IndustrySupervisor(Base):
    __tablename__ = "industry_supervisors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    job_title = Column(String, nullable=True)

    user = relationship("User", back_populates="supervisor_profile")
    organization = relationship("Organization", back_populates="supervisors")
    placements = relationship("Placement", back_populates="supervisor")

class Placement(Base):
    __tablename__ = "placements"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("industry_supervisors.id", ondelete="SET NULL"), nullable=True)
    placement_request_id = Column(Integer, ForeignKey("placement_requests.id", ondelete="SET NULL"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_weeks = Column(Integer, default=24, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected

    student = relationship("StudentProfile", back_populates="placements")
    organization = relationship("Organization", back_populates="placements")
    supervisor = relationship("IndustrySupervisor", back_populates="placements")
    logbook_entries = relationship("LogbookEntry", back_populates="placement")
    attendance_records = relationship("Attendance", back_populates="placement")
    assessments = relationship("Assessment", back_populates="placement")
    final_reports = relationship("FinalReport", back_populates="placement")

class LogbookEntry(Base):
    __tablename__ = "logbook_entries"

    id = Column(Integer, primary_key=True, index=True)
    placement_id = Column(Integer, ForeignKey("placements.id", ondelete="CASCADE"), nullable=False)
    week_number = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    activities = Column(Text, nullable=False)
    monday_activity = Column(Text, nullable=True)
    tuesday_activity = Column(Text, nullable=True)
    wednesday_activity = Column(Text, nullable=True)
    thursday_activity = Column(Text, nullable=True)
    friday_activity = Column(Text, nullable=True)
    saturday_activity = Column(Text, nullable=True)
    weekly_summary = Column(Text, nullable=True)
    tools_used = Column(String, nullable=True)
    challenges = Column(Text, nullable=True)
    learning_outcome = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft, submitted, approved, rejected, revision_requested

    placement = relationship("Placement", back_populates="logbook_entries")
    feedback = relationship("EntryFeedback", back_populates="entry")
    evidence_files = relationship("EvidenceFile", back_populates="entry")
    ai_reviews = relationship("AIReview", back_populates="entry")

class EntryFeedback(Base):
    __tablename__ = "entry_feedback"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("logbook_entries.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comment = Column(Text, nullable=False)
    decision = Column(String, nullable=False)  # approved, rejected, revision_requested
    score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    entry = relationship("LogbookEntry", back_populates="feedback")

class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("logbook_entries.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)

    entry = relationship("LogbookEntry", back_populates="evidence_files")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    placement_id = Column(Integer, ForeignKey("placements.id", ondelete="CASCADE"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # present, absent, excused
    note = Column(String, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    placement = relationship("Placement", back_populates="attendance_records")

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    placement_id = Column(Integer, ForeignKey("placements.id", ondelete="CASCADE"), nullable=False)
    assessor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    punctuality_score = Column(Integer, default=0)
    technical_score = Column(Integer, default=0)
    communication_score = Column(Integer, default=0)
    professionalism_score = Column(Integer, default=0)
    total_score = Column(Integer, default=0)
    remarks = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft, finalized

    placement = relationship("Placement", back_populates="assessments")

class AIReview(Base):
    __tablename__ = "ai_reviews"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("logbook_entries.id", ondelete="CASCADE"), nullable=False)
    completeness_score = Column(Integer, nullable=False)
    suggestions = Column(JSON, nullable=False)  # JSON list of strings
    category = Column(String, nullable=False)
    repetition_flag = Column(Boolean, default=False)
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    entry = relationship("LogbookEntry", back_populates="ai_reviews")

class FinalReport(Base):
    __tablename__ = "final_reports"

    id = Column(Integer, primary_key=True, index=True)
    placement_id = Column(Integer, ForeignKey("placements.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String, nullable=False)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="submitted")  # submitted, approved, rejected
    reviewer_comment = Column(Text, nullable=True)

    placement = relationship("Placement", back_populates="final_reports")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info")  # info, warning, success
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AcademicSession(Base):
    __tablename__ = "academic_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    registration_start = Column(Date, nullable=False)
    registration_end = Column(Date, nullable=False)
    placement_deadline = Column(Date, nullable=False)
    assessment_deadline = Column(Date, nullable=False)
    status = Column(String, default="active")  # active, archived
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PlacementRequest(Base):
    __tablename__ = "placement_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True)
    proposed_company_name = Column(String, nullable=False)
    proposed_company_address = Column(String, nullable=False)
    proposed_company_industry = Column(String, nullable=True)
    proposed_company_email = Column(String, nullable=True)
    proposed_company_phone = Column(String, nullable=True)
    proposed_supervisor_name = Column(String, nullable=False)
    proposed_supervisor_job_title = Column(String, nullable=False)
    proposed_supervisor_email = Column(String, nullable=False)
    proposed_supervisor_phone = Column(String, nullable=False)
    proposed_supervisor_experience = Column(Integer, nullable=True)
    proposed_supervisor_department = Column(String, nullable=True)
    relationship_to_student = Column(String, nullable=True)
    conflict_declaration = Column(Text, nullable=True)
    company_representative_name = Column(String, nullable=True)
    company_representative_email = Column(String, nullable=True)
    hr_invitation_token = Column(String, nullable=True)
    hr_confirmed = Column(Boolean, default=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_weeks = Column(Integer, default=24, nullable=False)
    how_obtained = Column(String, nullable=True)
    proposed_duties = Column(Text, nullable=True)
    technical_areas = Column(JSON, nullable=True)
    expected_work = Column(Text, nullable=True)
    status = Column(String, default="draft")
    appeal_description = Column(Text, nullable=True)
    is_disputed = Column(Boolean, default=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    student = relationship("StudentProfile")
    invitations = relationship("SupervisorInvitation", back_populates="placement_request", cascade="all, delete-orphan")
    confirmations = relationship("SupervisorConfirmation", back_populates="placement_request", cascade="all, delete-orphan")
    evidence = relationship("VerificationEvidence", back_populates="placement_request", cascade="all, delete-orphan")
    reviews = relationship("VerificationReview", back_populates="placement_request", cascade="all, delete-orphan")
    comparisons = relationship("FieldComparison", back_populates="placement_request", cascade="all, delete-orphan")
    history = relationship("StatusHistory", back_populates="placement_request", cascade="all, delete-orphan")

class SupervisorInvitation(Base):
    __tablename__ = "supervisor_invitations"

    id = Column(Integer, primary_key=True, index=True)
    placement_request_id = Column(Integer, ForeignKey("placement_requests.id", ondelete="CASCADE"), nullable=False)
    email = Column(String, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")

    placement_request = relationship("PlacementRequest", back_populates="invitations")

class SupervisorConfirmation(Base):
    __tablename__ = "supervisor_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    placement_request_id = Column(Integer, ForeignKey("placement_requests.id", ondelete="CASCADE"), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    confirmation_statement = Column(Boolean, default=False)
    confirmed_at = Column(DateTime, default=datetime.datetime.utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    placement_request = relationship("PlacementRequest", back_populates="confirmations")

class VerificationEvidence(Base):
    __tablename__ = "verification_evidence"

    id = Column(Integer, primary_key=True, index=True)
    placement_request_id = Column(Integer, ForeignKey("placement_requests.id", ondelete="CASCADE"), nullable=False)
    submitted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    evidence_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    issuer_name = Column(String, nullable=True)
    issuer_contact = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="pending")
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    placement_request = relationship("PlacementRequest", back_populates="evidence")

class VerificationReview(Base):
    __tablename__ = "verification_reviews"

    id = Column(Integer, primary_key=True, index=True)
    placement_request_id = Column(Integer, ForeignKey("placement_requests.id", ondelete="CASCADE"), nullable=False)
    coordinator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    reviewed_at = Column(DateTime, default=datetime.datetime.utcnow)

    placement_request = relationship("PlacementRequest", back_populates="reviews")

class FieldComparison(Base):
    __tablename__ = "field_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    placement_request_id = Column(Integer, ForeignKey("placement_requests.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String, nullable=False)
    student_value = Column(Text, nullable=True)
    supervisor_value = Column(Text, nullable=True)
    match_status = Column(String, nullable=False)

    placement_request = relationship("PlacementRequest", back_populates="comparisons")

class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    placement_request_id = Column(Integer, ForeignKey("placement_requests.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    placement_request = relationship("PlacementRequest", back_populates="history")
