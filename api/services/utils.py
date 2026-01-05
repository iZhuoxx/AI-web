import os
from typing import Optional
from api.settings import settings


def get_headers() -> dict:
    if not settings.API_KEY:
        # Fail fast with clear message instead of letting OpenAI return 401
        raise RuntimeError("Missing API_KEY. Set it in api/.env (API_KEY=sk-...)")
    return {
        "Authorization": f"Bearer {settings.API_KEY}",
        "Content-Type": "application/json",
    }


def get_proxy() -> Optional[str]:
    """
    Return a single proxy URL string or None.
    Prefers settings.HTTPS_PROXY; falls back to common env vars.
    Works with httpx>=0.28 (AsyncClient(proxy=...)).
    """
    return (
        settings.HTTPS_PROXY
        or os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("HTTP_PROXY")
        or os.getenv("http_proxy")
        or None
    )
