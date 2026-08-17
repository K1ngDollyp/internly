# Internly - Smart SIWES System

**Design and Implementation of a Smart Web-Based SIWES Management, Monitoring, and Assessment System with Custom Local AI-Assisted Logbook Evaluation**

---

## Technical Stack
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **Database**: Supabase (PostgreSQL) or Local SQLite fallback
- **AI Engine**: Custom self-contained local parser (completeness metrics, similarity repetition detector, domain category classifier)
- **Frontend**: HTML5, Vanilla CSS (Premium dark mode, glassmorphism UI, Outfit/Inter typography), Vanilla JavaScript

---

## Directory Structure
- `app/`: Python package directory for core configurations, models, schemas, routing, static UI elements.
- `uploads/`: Document upload directory for evidence and final report files.
- `tests/`: Automated unit and integration tests.

---

## Setup & Local Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory (or use the configured default):
   ```ini
   DATABASE_URL=postgresql://postgres.xxx:your-password@aws-0-us-west-1.pooler.supabase.com:5432/postgres
   JWT_SECRET=super-secret-key-change-in-production-1234567890
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```
   *Note: If no PostgreSQL link is configured, the application automatically falls back to a local SQLite database (`siwes.db`) to ensure immediate execution.*

3. **Run Automated Tests**:
   To run the verification suite:
   ```bash
   pytest
   ```

4. **Launch the System**:
   To start the backend and serve the premium dashboard SPA interface:
   ```bash
   uvicorn app.main:app --reload
   ```
   - Open your browser to: `http://127.0.0.1:8000`
   - Access Swagger API documentation at: `http://127.0.0.1:8000/docs`
