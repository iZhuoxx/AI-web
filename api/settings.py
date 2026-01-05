import csv
from pathlib import Path
from typing import List, Optional, Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = str((Path(__file__).resolve().parent / ".env"))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=True)

    API_KEY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None
    INTERNAL_TOKEN: Optional[str] = None

    DATABASE_URL: Optional[str] = None
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_DISABLE_POOL: bool = False

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    JWT_SECRET_KEY: str = "dev-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    SESSION_COOKIE_NAME: str = "aiweb_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "lax"
    CSRF_SECRET: str = "dev-csrf-secret"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_TOKEN_TTL_SECONDS: int = 60 * 60 * 8

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: Optional[str] = None
    AWS_S3_ENDPOINT_URL: Optional[str] = None

settings = Settings()
