"""
Email Service Module
--------------------
Handles sending automated email notifications (supervisor invitations, logbook alert updates)
using SMTP / Resend API settings, with a safe fallback logging mechanism for local environments.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "notifications@internly2026.vercel.app")

class EmailService:

    @staticmethod
    def send_email(to_email: str, subject: str, body_html: str) -> bool:
        """Dispatches an HTML email via SMTP or logs to console if credentials are not set."""
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            print(f"[EMAIL SERVICE MOCK] To: {to_email} | Subject: {subject}")
            print(f"[EMAIL BODY]: {body_html[:200]}...")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Internly SIWES Portal <{SENDER_EMAIL}>"
            msg["To"] = to_email

            html_part = MIMEText(body_html, "html")
            msg.attach(html_part)

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())
            print(f"[EMAIL SERVICE SUCCESS] Email sent to {to_email}")
            return True
        except Exception as e:
            print(f"[EMAIL SERVICE ERROR] Failed to send email to {to_email}: {e}")
            return False

    @classmethod
    def send_supervisor_invitation(cls, supervisor_email: str, supervisor_name: str, student_name: str, company_name: str, invite_link: str):
        """Sends the 7-day tokenized placement confirmation invitation to the proposed supervisor."""
        subject = f"SIWES Placement Verification Request for {student_name} - {company_name}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; border: 1px solid #e0e0e0;">
                <h2 style="color: #4F46E5; margin-top: 0;">SIWES Internship Verification Invitation</h2>
                <p>Hello <strong>{supervisor_name}</strong>,</p>
                <p><strong>{student_name}</strong> has registered a Students Industrial Work Experience Scheme (SIWES) placement proposal at <strong>{company_name}</strong> listing you as their proposed Industry Supervisor.</p>
                <p>Please click the button below to confirm your organization's affiliation, verify placement details, and upload the official Acceptance Letter:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invite_link}" style="background-color: #4F46E5; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-weight: bold; display: inline-block;">Confirm Placement & Complete Verification</a>
                </div>
                <p style="font-size: 13px; color: #666;">If the button does not work, copy and paste this secure link into your browser:<br>
                <a href="{invite_link}" style="color: #4F46E5;">{invite_link}</a></p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #888;">This invitation token is valid for 7 days. Generated automatically via Internly SIWES Portal.</p>
            </div>
        </body>
        </html>
        """
        return cls.send_email(supervisor_email, subject, html_content)
