from __future__ import annotations

from fastapi import APIRouter

from api.settings import settings
from api.services.ai_registry import list_model_options, list_tool_options

router = APIRouter(tags=["ai-config"])


@router.get("/ai/config")
def get_ai_config():
    options = list_model_options()
    allowed = [key for key in settings.AI_MODEL_OPTIONS if key]
    if allowed:
        option_map = {opt.get("key"): opt for opt in options if opt.get("key")}
        options = [option_map[key] for key in allowed if key in option_map]

    return {
        "model_options": options,
        "model_defaults": settings.AI_MODEL_DEFAULTS,
        "tool_options": list_tool_options(),
        "tool_defaults": settings.AI_TOOL_DEFAULTS,
    }
