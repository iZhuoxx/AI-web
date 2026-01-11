from pathlib import Path
from typing import Any, Dict, List, Optional
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

    # --- AI model/tool registry (centralized configuration) ---
    # AI_MODELS maps public model keys to provider ids and UI labels.
    AI_MODELS: Dict[str, Dict[str, Any]] = {
        "gpt-4.1": {"id": "gpt-4.1", "label": "gpt-4.1", "supports_temperature": True},
        "gpt-5": {"id": "gpt-5", "label": "gpt-5", "supports_temperature": False},
        "gpt-5.1": {"id": "gpt-5.1", "label": "gpt-5.1", "supports_temperature": False},
        "gpt-5-mini": {
            "id": "gpt-5-mini-2025-08-07",
            "label": "gpt-5-mini-2025-08-07",
            "supports_temperature": False,
        },
        "gpt-4.1-nano": {"id": "gpt-4.1-nano", "label": "gpt-4.1-nano", "supports_temperature": True},
        "gpt-4o-transcribe": {
            "id": "gpt-4o-transcribe",
            "label": "gpt-4o-transcribe",
            "supports_temperature": True,
        },
    }
    # Defaults are scene keys -> model keys (not provider ids).
    AI_MODEL_DEFAULTS: Dict[str, str] = {
        "chat": "gpt-5-mini",
        "noteChat": "gpt-5-mini",
        "flashcard": "gpt-5-mini",
        "quiz": "gpt-5-mini",
        "quizSummary": "gpt-5-mini",
        "mindmap": "gpt-5-mini",
        "title": "gpt-5-mini",
        "audioTranscribe": "gpt-4o-transcribe",
        "audioRealtime": "gpt-4o-transcribe",
    }
    # Whitelist of model keys exposed to the frontend picker.
    AI_MODEL_OPTIONS: List[str] = [
        "gpt-4.1",
        "gpt-5",
        "gpt-5.1",
        "gpt-5-mini",
    ]

    # Tool definitions; meta fields are stripped before sending to the provider.
    AI_TOOLS: Dict[str, Dict[str, Any]] = {
        "image_generation": {"type": "image_generation", "label": "Image generation"},
        "file_search": {
            "type": "file_search",
            "label": "File search",
            "include": ["file_search_call.results"],
            "allow_overrides": ["vector_store_ids"],
        },
    }
    # Per-scene default tool keys used when the client omits tool selection.
    AI_TOOL_DEFAULTS: Dict[str, List[str]] = {
        "chat": ["image_generation"],
        "noteChat": ["file_search"],
    }

settings = Settings()
