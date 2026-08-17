from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Check if SQLite is used to set appropriate connection arguments
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif db_url.startswith("postgresql"):
    # Try psycopg2 first, fall back to pg8000 (pure Python, works on Vercel)
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)
        # pg8000 doesn't support sslmode param in URL, handle it via connect_args
        if "sslmode=require" in db_url:
            db_url = db_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_args = {"ssl_context": ssl_context}

engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
