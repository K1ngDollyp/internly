from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import sys
import traceback

# Determine base directory (works on both local and Vercel)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
IS_VERCEL = os.environ.get("VERCEL", False)
UPLOADS_DIR = "/tmp/uploads" if IS_VERCEL else os.path.join(BASE_DIR, "uploads")

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

# Debug endpoint — always available, even if DB fails
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "siwes-backend",
        "python": sys.version,
        "cwd": os.getcwd(),
        "base_dir": BASE_DIR,
        "static_dir": STATIC_DIR,
        "static_exists": os.path.isdir(STATIC_DIR),
        "env_db": bool(os.environ.get("DATABASE_URL")),
        "is_vercel": bool(IS_VERCEL),
    }

# Try to initialize database and routes — catch errors gracefully
startup_error = None
try:
    from app.core.database import engine, Base
    from app.routers import auth, students, placements, logbook, attendance, assessments, dashboards, ai_review, reports, verification, sessions

    # Initialize database tables
    Base.metadata.create_all(bind=engine)

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

except Exception as e:
    startup_error = traceback.format_exc()
    print(f"STARTUP ERROR: {startup_error}", file=sys.stderr)

# Create upload directory
try:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
except OSError:
    pass

# Mount static files and uploads
try:
    if os.path.isdir(UPLOADS_DIR):
        app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
    if os.path.isdir(STATIC_DIR):
        app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
except Exception:
    pass

@app.get("/")
def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "index.html not found", "static_dir": STATIC_DIR, "startup_error": startup_error})

@app.get("/debug")
def debug_info():
    """Debug endpoint to diagnose deployment issues."""
    return {
        "startup_error": startup_error,
        "cwd": os.getcwd(),
        "base_dir": BASE_DIR,
        "static_dir": STATIC_DIR,
        "uploads_dir": UPLOADS_DIR,
        "static_exists": os.path.isdir(STATIC_DIR),
        "index_exists": os.path.isfile(os.path.join(STATIC_DIR, "index.html")),
        "env_vars_set": {
            "DATABASE_URL": bool(os.environ.get("DATABASE_URL")),
            "JWT_SECRET": bool(os.environ.get("JWT_SECRET")),
        },
        "python_version": sys.version,
        "is_vercel": bool(IS_VERCEL),
    }
