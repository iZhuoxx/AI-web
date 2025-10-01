# api/services/openai_client.py
import httpx
from typing import AsyncIterator, Dict, Any
from contextlib import asynccontextmanager

from api.services.utils import get_headers, get_proxy
from api.settings import settings

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_COMP_URL = "https://api.openai.com/v1/completions"
OPENAI_CHAT_COMP_URL = "https://api.openai.com/v1/chat/completions"




@asynccontextmanager
async def create_client(timeout: float = 60.0):
    proxy = get_proxy()
    kwargs: Dict[str, Any] = {"timeout": timeout}
    try:
        client = httpx.AsyncClient(proxy=proxy, **kwargs) if proxy else httpx.AsyncClient(**kwargs)
    except TypeError:
        proxies = {"http://": proxy, "https://": proxy} if proxy else None
        client = httpx.AsyncClient(proxies=proxies, **kwargs)
    try:
        yield client
    finally:
        await client.aclose()


# --- Responses API ---

async def responses_stream(payload: Dict[str, Any]) -> AsyncIterator[str]:
    # data = normalize_responses_payload(payload)
    data = payload
    print("DEBUG final payload (stream):", data)  # 调试用
    async with create_client() as client:
        async with client.stream(
            "POST",
            OPENAI_RESPONSES_URL,
            json={**data, "stream": True},
            headers=get_headers(),
        ) as r:
            if r.status_code >= 400:
                body = await r.aread()
                print("[OpenAI error stream]", r.status_code, body.decode(errors="ignore"))
                r.raise_for_status()

            async for line in r.aiter_lines():
                if line:
                    yield line


