from __future__ import annotations

from typing import Any, Dict, List


def _coerce_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out
    return []


def _has_file_search(tools: Any) -> bool:
    if isinstance(tools, dict):
        return tools.get("type") == "file_search"
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict) and tool.get("type") == "file_search":
                return True
    return False


def build_responses_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a simplified payload into the OpenAI Responses API schema.
    If `input` already exists, it will be returned as-is (with minimal decoration).
    """
    if "input" in raw:
        payload = dict(raw)
        tools = payload.get("tools")
        includes = _coerce_str_list(payload.get("includes") or payload.get("include"))
        include_set = set(includes)
        if _has_file_search(tools):
            include_set.add("file_search_call.results")
        if include_set:
            payload["include"] = list(include_set)
        return payload

    model = str(raw.get("model") or "")
    system_prompt = str(raw.get("system_prompt") or raw.get("systemPrompt") or "").strip()
    text = str(raw.get("text") or raw.get("message") or "").strip()
    images = _coerce_str_list(raw.get("images"))
    files = raw.get("files") if isinstance(raw.get("files"), list) else []
    tools = raw.get("tools")
    includes = _coerce_str_list(raw.get("includes") or raw.get("include"))
    prev_id = raw.get("previous_response_id") or raw.get("previousResponseId")
    temperature = raw.get("temperature")
    max_output_tokens = raw.get("max_output_tokens") or raw.get("maxTokens")
    reasoning = raw.get("reasoning")

    input_blocks: List[Dict[str, Any]] = []
    if system_prompt:
        input_blocks.append({"role": "system", "content": [{"type": "input_text", "text": system_prompt}]})

    user_content: List[Dict[str, Any]] = []
    if text:
        user_content.append({"type": "input_text", "text": text})
    for url in images:
        user_content.append({"type": "input_image", "image_url": url})
    for f in files:
        if not isinstance(f, dict):
            continue
        file_id = f.get("file_id") or f.get("fileId")
        if isinstance(file_id, str) and file_id.strip():
            user_content.append({"type": "input_file", "file_id": file_id.strip()})
        file_text = f.get("text")
        if isinstance(file_text, str) and file_text.strip():
            name = f.get("name") or "file"
            label = f"[截断] {name}" if f.get("truncated") else str(name)
            user_content.append({"type": "input_text", "text": f"【文件：{label}】\n{file_text}"})

    if not user_content and not input_blocks:
        raise ValueError("请求体缺少内容")

    input_blocks.append({"role": "user", "content": user_content})

    include_set = set(includes)
    if _has_file_search(tools):
        include_set.add("file_search_call.results")

    payload: Dict[str, Any] = {
        "model": model,
        "input": input_blocks,
    }
    if tools is not None:
        payload["tools"] = tools
    if include_set:
        payload["include"] = list(include_set)
    if isinstance(prev_id, str) and prev_id.strip():
        payload["previous_response_id"] = prev_id.strip()
    if not model.lower().startswith("gpt-5") and isinstance(temperature, (int, float)):
        payload["temperature"] = float(temperature)
    if isinstance(max_output_tokens, (int, float)):
        payload["max_output_tokens"] = int(max_output_tokens)
    if reasoning is not None:
        payload["reasoning"] = reasoning

    return payload
