import httpx
from typing import AsyncIterator, Dict, Any
from contextlib import asynccontextmanager

from api.services.utils import get_headers, get_proxy
from api.settings import settings

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_COMP_URL = "https://api.openai.com/v1/completions"
OPENAI_CHAT_COMP_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_CREDIT_URL = "https://api.openai.com/dashboard/billing/credit_grants"


# ---------- normalize helpers for /v1/responses ----------

def _ensure_text_content_list(text: str):
    # Must be 'input_text' for user input in the Responses API
    return [{"type": "input_text", "text": text}]


def _fix_content_type(input_list):
    """
    遍历 input 列表，把 type='text' 改为 'input_text'
    """
    for item in input_list:
        if "content" in item and isinstance(item["content"], list):
            for c in item["content"]:
                if isinstance(c, dict) and c.get("type") == "text":
                    c["type"] = "input_text"
    return input_list


def normalize_responses_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize various legacy shapes to the required /v1/responses shape.
    强制把 content type 从 'text' 修正为 'input_text'
    """
    normalized: Dict[str, Any] = {}
    model = payload.get("model") or "gpt-4o-mini"
    normalized["model"] = model

    # already correct?
    if "input" in payload and isinstance(payload["input"], list):
        normalized["input"] = _fix_content_type(payload["input"])
        for k in ("temperature", "max_output_tokens", "metadata"):
            if k in payload:
                normalized[k] = payload[k]
        return normalized

    # legacy: messages -> input
    if "messages" in payload and isinstance(payload["messages"], list):
        input_list = []
        for m in payload["messages"]:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                input_list.append({"role": role, "content": content})
            else:
                input_list.append({"role": role, "content": _ensure_text_content_list(str(content))})
        normalized["input"] = _fix_content_type(input_list)
        return normalized

    # legacy: prompt -> single user turn
    if "prompt" in payload and isinstance(payload["prompt"], str):
        normalized["input"] = _ensure_text_content_list(payload["prompt"])
        normalized["input"] = [{"role": "user", "content": normalized["input"]}]
        return normalized

    # fallback: if 'text' provided directly
    if "text" in payload and isinstance(payload["text"], str):
        normalized["input"] = [{"role": "user", "content": _ensure_text_content_list(payload["text"])}]
        return normalized

    # question
    if "question" in payload and isinstance(payload["question"], str):
        normalized["input"] = [{"role": "user", "content": _ensure_text_content_list(payload["question"])}]
        return normalized

    raise ValueError("Invalid payload for /v1/responses. Provide `input`, or legacy `messages`/`prompt`/`text`.")


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
    data = normalize_responses_payload(payload)
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


async def responses_once(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = normalize_responses_payload(payload)
    print("DEBUG final payload (once):", data)  # 调试用
    async with create_client() as client:
        resp = await client.post(
            OPENAI_RESPONSES_URL,
            json={**data, "stream": False},
            headers=get_headers(),
        )
        if resp.status_code >= 400:
            print("[OpenAI error once]", resp.status_code, await resp.text())
        resp.raise_for_status()
        return resp.json()
