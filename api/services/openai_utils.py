from __future__ import annotations

from typing import Any, Dict, List

from fastapi import HTTPException

from api.settings import settings
from api.services.ai_registry import resolve_model_key, resolve_model_value, resolve_tools


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


def build_responses_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a simplified payload into the OpenAI Responses API schema.
    If `input` already exists, it will be returned as-is (with minimal decoration).
    """
    if "input" in raw:
        payload = dict(raw)
        raw_tool_keys = payload.get("tool_keys") if "tool_keys" in payload else payload.get("toolKeys")
        tool_keys = _coerce_str_list(raw_tool_keys)
        tool_overrides = payload.get("tool_overrides") or payload.get("toolOverrides")
        if payload.get("tools") is not None and not tool_keys:
            raise HTTPException(status_code=400, detail="Use tool_keys instead of tools")

        model_info = None
        model_key = payload.get("model_key") or payload.get("modelKey")
        if model_key:
            model_info = resolve_model_key(model_key, default_key=settings.AI_MODEL_DEFAULTS.get("chat"))
            payload["model"] = model_info.model
        elif payload.get("model"):
            model_info = resolve_model_value(payload.get("model"))
            payload["model"] = model_info.model
        else:
            model_info = resolve_model_key(None, default_key=settings.AI_MODEL_DEFAULTS.get("chat"))
            payload["model"] = model_info.model

        includes = _coerce_str_list(payload.get("includes") or payload.get("include"))
        include_set = set(includes)

        tool_key_arg = tool_keys if raw_tool_keys is not None else None
        tools, tool_includes = resolve_tools(
            tool_key_arg,
            default_keys=settings.AI_TOOL_DEFAULTS.get("chat"),
            overrides=tool_overrides,
        )
        if tools:
            payload["tools"] = tools
            include_set.update(tool_includes)

        if include_set:
            payload["include"] = list(include_set)

        if model_info and not model_info.supports_temperature:
            payload.pop("temperature", None)

        return payload

    model_key = raw.get("model_key") or raw.get("modelKey")
    system_prompt = str(raw.get("system_prompt") or raw.get("systemPrompt") or "").strip()
    text = str(raw.get("text") or raw.get("message") or "").strip()
    images = _coerce_str_list(raw.get("images"))
    files = raw.get("files") if isinstance(raw.get("files"), list) else []
    raw_tool_keys = raw.get("tool_keys") if "tool_keys" in raw else raw.get("toolKeys")
    tool_keys = _coerce_str_list(raw_tool_keys)
    tool_overrides = raw.get("tool_overrides") or raw.get("toolOverrides")
    if raw.get("tools") is not None and not tool_keys:
        raise HTTPException(status_code=400, detail="Use tool_keys instead of tools")
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
    tool_key_arg = tool_keys if raw_tool_keys is not None else None
    tools, tool_includes = resolve_tools(
        tool_key_arg,
        default_keys=settings.AI_TOOL_DEFAULTS.get("chat"),
        overrides=tool_overrides,
    )
    include_set.update(tool_includes)

    model_info = resolve_model_key(model_key, default_key=settings.AI_MODEL_DEFAULTS.get("chat"))
    payload: Dict[str, Any] = {
        "model": model_info.model,
        "input": input_blocks,
    }
    if tools:
        payload["tools"] = tools
    if include_set:
        payload["include"] = list(include_set)
    if isinstance(prev_id, str) and prev_id.strip():
        payload["previous_response_id"] = prev_id.strip()
    if model_info.supports_temperature and isinstance(temperature, (int, float)):
        payload["temperature"] = float(temperature)
    if isinstance(max_output_tokens, (int, float)):
        payload["max_output_tokens"] = int(max_output_tokens)
    if reasoning is not None:
        payload["reasoning"] = reasoning

    return payload


def _coerce_text_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "output_text", "value"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
            if isinstance(candidate, dict):
                nested = _coerce_text_value(candidate)
                if nested:
                    return nested
    return ""


def extract_text_from_response(payload: dict) -> str:
    """Extract text content from an OpenAI Responses API payload."""
    if not isinstance(payload, dict):
        return ""

    output_text = payload.get("output_text")
    if isinstance(output_text, list):
        for item in output_text:
            text_val = _coerce_text_value(item)
            if text_val.strip():
                return text_val
    else:
        text_val = _coerce_text_value(output_text)
        if text_val.strip():
            return text_val

    output = payload.get("output") or []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            text_val = _coerce_text_value(item.get("text"))
            if text_val.strip():
                return text_val
            content_list = item.get("content") or []
            if isinstance(content_list, dict):
                text_val = _coerce_text_value(content_list)
                if text_val.strip():
                    return text_val
            elif isinstance(content_list, list):
                for content in content_list:
                    if not isinstance(content, dict):
                        continue
                    text_val = _coerce_text_value(content)
                    if text_val.strip():
                        return text_val
    return ""


def extract_structured_output(payload: dict) -> dict:
    """Extract the first structured/json response block from a Responses API payload."""
    if not isinstance(payload, dict):
        return {}

    parsed = payload.get("output_parsed")
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list) and parsed:
        first = parsed[0]
        if isinstance(first, dict):
            return first

    output = payload.get("output") or []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            item_parsed = item.get("parsed")
            if isinstance(item_parsed, dict):
                return item_parsed
            if isinstance(item_parsed, list):
                for candidate in item_parsed:
                    if isinstance(candidate, dict):
                        return candidate

            content_list = item.get("content") or []
            if isinstance(content_list, list):
                for content in content_list:
                    if not isinstance(content, dict):
                        continue
                    parsed_val = content.get("parsed")
                    if isinstance(parsed_val, dict):
                        return parsed_val
                    if isinstance(parsed_val, list):
                        for candidate in parsed_val:
                            if isinstance(candidate, dict):
                                return candidate
                    json_val = content.get("json")
                    if isinstance(json_val, dict):
                        return json_val
                    text_val = content.get("text")
                    if isinstance(text_val, str) and text_val.strip():
                        try:
                            import json

                            return json.loads(text_val)
                        except Exception:
                            continue
            elif isinstance(content_list, dict):
                parsed_val = content_list.get("parsed")
                if isinstance(parsed_val, dict):
                    return parsed_val
                json_val = content_list.get("json")
                if isinstance(json_val, dict):
                    return json_val

    return {}
