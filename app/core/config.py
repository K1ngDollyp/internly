import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./siwes.db"
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Supabase Storage configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = None
try:
    settings = Settings()
except Exception:
    settings = None
