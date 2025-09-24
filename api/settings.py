# api/settings.py
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings  

ENV_FILE = str((Path(__file__).resolve().parent / ".env"))

class Settings(BaseSettings):
    API_KEY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    INTERNAL_TOKEN: Optional[str] = None

    class Config:
        env_file = ENV_FILE
        case_sensitive = True

settings = Settings()
