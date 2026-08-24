import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app as fastapi_app
from app.core.database import Base, get_db
from app.services.ai_service import LogbookAIModel
import app.models  # Crucial to register schemas in metadata

import os

# File-based SQLite for testing to maintain tables across connections
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_siwes.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        if os.path.exists("test_siwes.db"):
            os.remove("test_siwes.db")
    except Exception:
        pass

client = TestClient(fastapi_app)

def test_auth_registration_and_login():
    # Register student
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Student",
            "email": "student@test.com",
            "password": "securepassword123",
            "role": "student"
        }
    )
    assert reg_response.status_code == 200
    assert reg_response.json()["email"] == "student@test.com"
    assert reg_response.json()["role"] == "student"

    # Login using OAuth2 form-urlencoded parameters
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "student@test.com",
            "password": "securepassword123"
        }
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    assert login_response.json()["role"] == "student"

def test_register_rejects_coordinator_or_admin_role():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Rogue User",
            "email": "rogue@test.com",
            "password": "password123",
            "role": "coordinator"
        }
    )
    assert response.status_code == 400

def test_csv_export_unauthenticated_rejected():
    response = client.get("/api/v1/reports/export/csv")
    assert response.status_code == 401

def test_ai_logbook_evaluator():
    # Empty entry test
    empty_eval = LogbookAIModel.evaluate_entry(
        activities="",
        tools_used="",
        challenges="",
        learning_outcome=""
    )
    assert empty_eval["completenessScore"] == 0
    assert "General IT" in empty_eval["category"] or "Unclassified" in empty_eval["category"]

    # Incomplete entry test
    incomplete_eval = LogbookAIModel.evaluate_entry(
        activities="Worked on database design.",
        tools_used="SQL",
        challenges="",
        learning_outcome=""
    )
    assert incomplete_eval["completenessScore"] < 50
    assert len(incomplete_eval["suggestions"]) > 0

    # High quality entry test with software development words
    full_eval = LogbookAIModel.evaluate_entry(
        activities="I designed and implemented the backend REST API endpoints using FastAPI. Configured router paths, database schemas, and written unit tests for auth workflows. I successfully integrated the local AI evaluator and resolved database issues.",
        tools_used="FastAPI, SQLAlchemy, Pytest, Git",
        challenges="Had a challenge connecting to database tables due to circular imports, resolved by moving references to a separate module.",
        learning_outcome="Mastered asynchronous requests in Python, standard database modeling conventions, and repository design patterns."
    )
    assert full_eval["completenessScore"] >= 80
    assert "Software Engineering" in full_eval["category"]
    assert full_eval["repetitionFlag"] is False

def test_ai_logbook_similarity_flag():
    past_activities = ["Developed web pages with React framework."]
    
    dup_eval = LogbookAIModel.evaluate_entry(
        activities="Developed web pages with React framework.",
        tools_used="React",
        challenges="None",
        learning_outcome="React coding",
        previous_entries=past_activities
    )
    assert dup_eval["repetitionFlag"] is True
    assert any("similarity" in s for s in dup_eval["suggestions"])

def test_verification_workflow():
    # 1. Register Student
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Ade", "email": "ade@test.com", "password": "pass", "role": "student"}
    )
    login = client.post("/api/v1/auth/login", data={"username": "ade@test.com", "password": "pass"})
    student_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {student_token}"}

    # Setup Student profile
    client.patch("/api/v1/students/me", json={"matric_number": "123", "department": "CS", "level": "400"}, headers=headers)

    # 1.1 Create Coordinator in DB directly (since public registration prohibits coordinator self-registration)
    from app.models.siwes import User
    from app.core.security import get_password_hash
    db = TestingSessionLocal()
    c_user = User(full_name="Coordinator", email="coord@test.com", password_hash=get_password_hash("pass"), role="coordinator", status="active")
    db.add(c_user)
    db.commit()
    db.close()

    coord_login = client.post("/api/v1/auth/login", data={"username": "coord@test.com", "password": "pass"})
    coord_token = coord_login.json()["access_token"]
    coord_headers = {"Authorization": f"Bearer {coord_token}"}

    # Verify student identity first
    student_profiles_list = client.get("/api/v1/verification/students", headers=coord_headers)
    student_id_val = student_profiles_list.json()[0]["id"]
    client.post(f"/api/v1/verification/students/{student_id_val}/verify", headers=coord_headers)

    # 1.2 Coordinator creates active academic session
    client.post(
        "/api/v1/sessions",
        json={
            "name": "2026 SIWES Programme",
            "registration_start": "2026-08-01",
            "registration_end": "2026-08-30",
            "placement_deadline": "2026-09-15",
            "assessment_deadline": "2026-12-15"
        },
        headers=coord_headers
    )

    # 2. Save Request Draft (Session should auto-associate)
    draft_res = client.post(
        "/api/v1/verification/request",
        json={
            "proposed_company_name": "BrightTech Ltd",
            "proposed_company_address": "Ikeja",
            "proposed_supervisor_name": "John",
            "proposed_supervisor_job_title": "Lead",
            "proposed_supervisor_email": "john@test.com",
            "proposed_supervisor_phone": "123",
            "start_date": "2026-08-01",
            "end_date": "2026-11-01"
        },
        headers=headers
    )
    assert draft_res.status_code == 200
    req_id = draft_res.json()["id"]
    assert draft_res.json()["session_id"] is not None

    # 3. Submit Request to get Invitation Link
    sub_res = client.post(f"/api/v1/verification/request/{req_id}/submit", headers=headers)
    assert sub_res.status_code == 200
    token = sub_res.json()["invitation_token"]

    # 4. Fetch invitation details publicly
    inv_res = client.get(f"/api/v1/verification/invitation/{token}")
    assert inv_res.status_code == 200
    assert inv_res.json()["student_name"] == "Ade"

    # 5. Supervisor accepts invitation and registers
    acc_res = client.post(
        f"/api/v1/verification/invitation/{token}/accept",
        data={
            "full_name": "John Doe",
            "password": "supervisorpass",
            "phone": "123",
            "job_title": "Lead Engineer",
            "confirm_statement": True
        }
    )
    assert acc_res.status_code == 200

    # Login supervisor
    sv_login = client.post("/api/v1/auth/login", data={"username": "john@test.com", "password": "supervisorpass"})
    sv_token = sv_login.json()["access_token"]
    sv_headers = {"Authorization": f"Bearer {sv_token}"}

    # 6. Supervisor confirms and uploads evidence
    import io
    dummy_file = io.BytesIO(b"acceptance letter content")
    conf_res = client.post(
        f"/api/v1/verification/request/{req_id}/confirm",
        data={
            "evidence_type": "Acceptance Letter",
            "title": "My Letter",
            "field_confirmations": '{"company_name": true, "company_address": true, "supervisor_name": true, "supervisor_job_title": true, "start_date": true, "end_date": true}',
            "field_corrections": '{"company_name": "", "company_address": "", "supervisor_name": "", "supervisor_job_title": "", "start_date": "", "end_date": ""}'
        },
        files={"file": ("letter.pdf", dummy_file, "application/pdf")},
        headers=sv_headers
    )
    assert conf_res.status_code == 200

    # Coordinator reviews detail
    det_res = client.get(f"/api/v1/verification/request/{req_id}/detail", headers=coord_headers)
    assert det_res.status_code == 200
    assert len(det_res.json()["comparisons"]) > 0

    # 8. Coordinator approves
    review_res = client.post(
        f"/api/v1/verification/request/{req_id}/review",
        json={"decision": "approved", "reason": "All checks match!"},
        headers=coord_headers
    )
    assert review_res.status_code == 200

    # 9. Verify placement promoted to active and logbook accessible
    pl_res = client.get("/api/v1/placements/me", headers=headers)
    assert pl_res.status_code == 200
    assert pl_res.json()["status"] == "approved"
