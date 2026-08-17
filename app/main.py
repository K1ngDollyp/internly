from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.database import engine, Base
from app.routers import auth, students, placements, logbook, attendance, assessments, dashboards, ai_review, reports, verification, sessions
import os

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart SIWES Management and Monitoring System",
    description="Backend API and frontend interface for the SIWES Management System",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefix versioning
API_PREFIX = "/api/v1"

# Include routers
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(students.router, prefix=API_PREFIX)
app.include_router(placements.router, prefix=API_PREFIX)
app.include_router(logbook.router, prefix=API_PREFIX)
app.include_router(attendance.router, prefix=API_PREFIX)
app.include_router(assessments.router, prefix=API_PREFIX)
app.include_router(dashboards.router, prefix=API_PREFIX)
app.include_router(ai_review.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(verification.router, prefix=API_PREFIX)
app.include_router(sessions.router, prefix=API_PREFIX)

# Create folders if they do not exist
if not os.path.exists("uploads"):
    os.makedirs("uploads")
if not os.path.exists("app/static"):
    os.makedirs("app/static")
if not os.path.exists("app/static/css"):
    os.makedirs("app/static/css")
if not os.path.exists("app/static/js"):
    os.makedirs("app/static/js")

# Mount Uploads directory to serve evidence and reports
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount Static directory for Frontend Assets
app.mount("/assets", StaticFiles(directory="app/static"), name="assets")

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "siwes-backend"}

@app.get("/")
def read_root():
    return FileResponse("app/static/index.html")
