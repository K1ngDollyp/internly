import os
import datetime
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models.siwes import User, StudentProfile, Placement, FinalReport, LogbookEntry, Assessment, AuditLog
from typing import List, Optional

router = APIRouter(prefix="/reports", tags=["Reports"])

# Set upload directory compatible with Vercel serverless filesystem (/tmp)
UPLOAD_DIR = "/tmp/uploads" if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "uploads"
if not os.path.exists(UPLOAD_DIR):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except Exception:
        UPLOAD_DIR = "/tmp"

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

@router.get("/pdf/{placement_id}")
def generate_printable_official_summary(
    placement_id: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generates a printable HTML document formatted like an official SIWES Departmental Summary Report
    with student placement details, attendance rate, weekly logbook logs, and supervisor grades.
    """
    from fastapi.responses import HTMLResponse
    from app.models.siwes import Attendance

    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement record not found")

    student_user = placement.student.user
    org_name = placement.organization.name if placement.organization else "Unspecified Host Organization"
    entries = db.query(LogbookEntry).filter(LogbookEntry.placement_id == placement_id).order_by(LogbookEntry.week_number.asc()).all()
    assessment = db.query(Assessment).filter(Assessment.placement_id == placement_id).first()
    
    # Calculate attendance statistics
    attendances = db.query(Attendance).filter(Attendance.placement_id == placement_id).all()
    total_days = len(attendances)
    present_days = sum(1 for a in attendances if a.status == "present")
    attendance_rate = round((present_days / total_days * 100), 1) if total_days > 0 else 100.0

    # Build weekly logbook table HTML
    logbook_rows = ""
    for e in entries:
        score_display = f"{e.feedback[0].score}/100" if (e.feedback and e.feedback[0].score is not None) else "Pending"
        logbook_rows += f"""
        <tr>
            <td style="border: 1px solid #CBD5E1; padding: 8px; text-align: center;">Week {e.week_number}</td>
            <td style="border: 1px solid #CBD5E1; padding: 8px;">{e.activities}</td>
            <td style="border: 1px solid #CBD5E1; padding: 8px;">{e.tools_used or 'N/A'}</td>
            <td style="border: 1px solid #CBD5E1; padding: 8px; text-align: center;">{e.status.upper()}</td>
            <td style="border: 1px solid #CBD5E1; padding: 8px; text-align: center;">{score_display}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SIWES Official Departmental Summary Report</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1E293B; }}
            .header {{ text-align: center; border-bottom: 3px double #0F172A; padding-bottom: 16px; margin-bottom: 24px; }}
            .title {{ font-size: 20px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; color: #0F172A; }}
            .subtitle {{ font-size: 14px; color: #475569; margin-top: 4px; }}
            .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; font-size: 14px; }}
            .meta-card {{ background: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 6px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }}
            th {{ background: #0F172A; color: #FFF; border: 1px solid #0F172A; padding: 10px; text-align: left; }}
            .score-box {{ background: #F0FDF4; border: 2px solid #16A34A; padding: 16px; border-radius: 8px; text-align: center; font-size: 18px; font-weight: bold; color: #166534; }}
            .footer {{ margin-top: 40px; display: flex; justify-content: space-between; font-size: 12px; border-top: 1px solid #CBD5E1; padding-top: 16px; }}
            @media print {{ body {{ margin: 0; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">Students Industrial Work Experience Scheme (SIWES)</div>
            <div class="subtitle">Official Departmental Progress & Final Assessment Transcript</div>
        </div>

        <div class="meta-grid">
            <div class="meta-card">
                <strong>Student Name:</strong> {student_user.full_name}<br>
                <strong>Matriculation No:</strong> {placement.student.matric_number}<br>
                <strong>Department:</strong> {placement.student.department} (Level {placement.student.level})
            </div>
            <div class="meta-card">
                <strong>Host Organization:</strong> {org_name}<br>
                <strong>Placement Duration:</strong> {placement.start_date} to {placement.end_date} ({placement.duration_weeks} Wks)<br>
                <strong>Attendance Rate:</strong> {attendance_rate}% ({present_days}/{total_days} Days Present)
            </div>
        </div>

        <h3 style="color: #0F172A; border-bottom: 2px solid #E2E8F0; padding-bottom: 6px;">Weekly Logbook Submissions Summary</h3>
        <table>
            <thead>
                <tr>
                    <th style="width: 10%;">Week</th>
                    <th style="width: 45%;">Activities & Accomplishments</th>
                    <th style="width: 25%;">Tools & Technologies</th>
                    <th style="width: 10%; text-align: center;">Status</th>
                    <th style="width: 10%; text-align: center;">Score</th>
                </tr>
            </thead>
            <tbody>
                {logbook_rows if logbook_rows else "<tr><td colspan='5' style='text-align:center; padding: 16px; color:#64748B;'>No logbook entries logged.</td></tr>"}
            </tbody>
        </table>

        <h3 style="color: #0F172A; border-bottom: 2px solid #E2E8F0; padding-bottom: 6px;">Final Assessment Scoring Breakdown</h3>
        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; align-items: center;">
            <div>
                <p><strong>Punctuality & Attendance:</strong> {assessment.punctuality_score if assessment else 0} / 20</p>
                <p><strong>Technical Skill Acquisition:</strong> {assessment.technical_score if assessment else 0} / 40</p>
                <p><strong>Communication & Teamwork:</strong> {assessment.communication_score if assessment else 0} / 20</p>
                <p><strong>Professionalism & Work Ethics:</strong> {assessment.professionalism_score if assessment else 0} / 20</p>
                <p><strong>Supervisor Remarks:</strong> <em>{assessment.remarks if (assessment and assessment.remarks) else 'No remarks entered'}</em></p>
            </div>
            <div class="score-box">
                FINAL SIWES GRADE<br>
                <span style="font-size: 32px; color: #15803D;">{assessment.total_score if assessment else 0} / 100</span><br>
                <small style="font-weight: normal; color: #475569;">STATUS: {assessment.status.upper() if assessment else 'PENDING'}</small>
            </div>
        </div>

        <div class="footer">
            <div>Industry Supervisor Sign-off: _____________________</div>
            <div>Departmental Coordinator Sign-off: _____________________</div>
            <div>Generated via Internly SIWES Platform</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/export/csv")
def export_departmental_grades_csv(
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Exports a CSV spreadsheet containing all student SIWES placement records,
    matriculation numbers, departments, host companies, attendance rates, and final scores.
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from app.models.siwes import Attendance

    placements = db.query(Placement).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV Header Row
    writer.writerow([
        "Placement ID", "Student Name", "Matric Number", "Department", "Level",
        "Host Organization", "Start Date", "End Date", "Duration (Weeks)",
        "Attendance Rate (%)", "Punctuality (20)", "Technical Skill (40)",
        "Communication (20)", "Professionalism (20)", "Total Score (100)", "Status"
    ])

    for p in placements:
        student_user = p.student.user
        org_name = p.organization.name if p.organization else "Unspecified"
        assessment = db.query(Assessment).filter(Assessment.placement_id == p.id).first()
        
        # Calculate attendance percentage
        attendances = db.query(Attendance).filter(Attendance.placement_id == p.id).all()
        total_days = len(attendances)
        present_days = sum(1 for a in attendances if a.status == "present")
        att_rate = round((present_days / total_days * 100), 1) if total_days > 0 else 100.0

        writer.writerow([
            p.id,
            student_user.full_name,
            p.student.matric_number,
            p.student.department,
            p.student.level,
            org_name,
            p.start_date.isoformat() if p.start_date else "",
            p.end_date.isoformat() if p.end_date else "",
            p.duration_weeks,
            f"{att_rate}%",
            assessment.punctuality_score if assessment else 0,
            assessment.technical_score if assessment else 0,
            assessment.communication_score if assessment else 0,
            assessment.professionalism_score if assessment else 0,
            assessment.total_score if assessment else 0,
            p.status.upper()
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=SIWES_Departmental_Grades_Matrix.csv"}
    )

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

