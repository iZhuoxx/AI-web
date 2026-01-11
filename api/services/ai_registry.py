from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import HTTPException

from api.settings import settings

_TOOL_META_KEYS = {"label", "include", "allow_overrides"}


@dataclass(frozen=True)
class ModelInfo:
    key: str
    model: str
    supports_temperature: bool


def _normalize_key(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _load_model_entry(key: str) -> Dict[str, Any]:
    entry = settings.AI_MODELS.get(key)
    if entry is None:
        raise HTTPException(status_code=400, detail=f"Unsupported model_key: {key}")
    if isinstance(entry, str):
        return {"id": entry}
    if isinstance(entry, dict):
        return entry
    raise HTTPException(status_code=400, detail=f"Invalid model config for key: {key}")


def resolve_model_key(model_key: Optional[str], *, default_key: Optional[str]) -> ModelInfo:
    resolved_key = _normalize_key(model_key) or _normalize_key(default_key)
    if not resolved_key:
        raise HTTPException(status_code=400, detail="Missing model_key")
    entry = _load_model_entry(resolved_key)
    model_id = _normalize_key(entry.get("id") or entry.get("model"))
    if not model_id:
        raise HTTPException(status_code=400, detail=f"Missing model id for key: {resolved_key}")
    supports_temperature = bool(entry.get("supports_temperature", True))
    return ModelInfo(key=resolved_key, model=model_id, supports_temperature=supports_temperature)


def resolve_model_value(model_value: Optional[str]) -> ModelInfo:
    value = _normalize_key(model_value)
    if not value:
        raise HTTPException(status_code=400, detail="Missing model")
    for key, entry in settings.AI_MODELS.items():
        entry_dict = entry if isinstance(entry, dict) else {"id": entry}
        model_id = _normalize_key(entry_dict.get("id") or entry_dict.get("model"))
        if model_id == value:
            supports_temperature = bool(entry_dict.get("supports_temperature", True))
            return ModelInfo(key=key, model=model_id, supports_temperature=supports_temperature)
    raise HTTPException(status_code=400, detail=f"Unsupported model: {value}")


def resolve_tools(
    tool_keys: Optional[Iterable[str]],
    *,
    default_keys: Optional[Iterable[str]] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    keys_source = tool_keys if tool_keys is not None else default_keys or []
    normalized_keys = []
    for key in keys_source:
        cleaned = _normalize_key(key)
        if cleaned:
            normalized_keys.append(cleaned)

    unique_keys = []
    seen = set()
    for key in normalized_keys:
        if key in seen:
            continue
        seen.add(key)
        unique_keys.append(key)

    tools: List[Dict[str, Any]] = []
    includes: List[str] = []
    overrides = overrides if isinstance(overrides, dict) else {}

    for key in unique_keys:
        entry = settings.AI_TOOLS.get(key)
        if not isinstance(entry, dict):
            raise HTTPException(status_code=400, detail=f"Unsupported tool_key: {key}")
        include = entry.get("include") or []
        if isinstance(include, list):
            for item in include:
                cleaned = _normalize_key(item)
                if cleaned:
                    includes.append(cleaned)

        allow_overrides = entry.get("allow_overrides") or []
        tool_payload = {k: v for k, v in entry.items() if k not in _TOOL_META_KEYS}

        override_payload = overrides.get(key)
        if isinstance(override_payload, dict) and isinstance(allow_overrides, list):
            for field in allow_overrides:
                if field in override_payload:
                    tool_payload[field] = override_payload[field]

        tools.append(tool_payload)

    return tools, includes


def list_model_options() -> List[Dict[str, str]]:
    options: List[Dict[str, str]] = []
    for key, entry in settings.AI_MODELS.items():
        label = key
        if isinstance(entry, dict):
            entry_label = entry.get("label")
            if isinstance(entry_label, str) and entry_label.strip():
                label = entry_label.strip()
        options.append({"key": key, "label": label})
    return options


def list_tool_options() -> List[Dict[str, str]]:
    options: List[Dict[str, str]] = []
    for key, entry in settings.AI_TOOLS.items():
        if not isinstance(entry, dict):
            continue
        label = entry.get("label") if isinstance(entry.get("label"), str) else key
        tool_type = entry.get("type")
        option: Dict[str, str] = {"key": key, "label": label or key}
        if isinstance(tool_type, str):
            option["type"] = tool_type
        options.append(option)
    return options
