import csv
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import FieldValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = str((Path(__file__).resolve().parent / ".env"))
S3_KEYS_PATH = Path(__file__).resolve().parent / "s3-easylearn-user_accessKeys.csv"


def _read_s3_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load S3 credentials from the CSV helper file if present."""

    if not S3_KEYS_PATH.exists():
        return None, None
    try:
        with S3_KEYS_PATH.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            first = next(reader, None)
            if not first:
                return None, None
            return first.get("Access key ID"), first.get("Secret access key")
    except Exception:
        return None, None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=True)

    API_KEY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None
    INTERNAL_TOKEN: Optional[str] = None

    DATABASE_URL: str = "postgresql+psycopg://noteai:noteai@localhost:5432/appdb"
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

    @field_validator("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", mode="before")
    @classmethod
    def _fallback_s3_creds(
        cls, value: Optional[str], info: FieldValidationInfo
    ) -> Optional[str]:
        if value:
            return value
        access_key, secret_key = _read_s3_credentials()
        if info.field_name == "AWS_ACCESS_KEY_ID":
            return access_key
        if info.field_name == "AWS_SECRET_ACCESS_KEY":
            return secret_key
        return value


settings = Settings()
