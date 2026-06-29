"""Visual style presets shared between the API and pipeline."""
from __future__ import annotations

from typing import Any

VISUAL_STYLE_PRESETS: list[dict[str, Any]] = [
    {
        "value": "classical_antiquity",
        "label": "Classical Antiquity",
        "summary": "Warm marble statues, laurel wreaths, sunlit forums.",
        "prompt": "classical antiquity oil painting, marble statues, laurel wreath, golden sunlight, film grain",
    },
    {
        "value": "medieval",
        "label": "Medieval Chronicle",
        "summary": "Illuminated manuscripts, parchment textures, gothic arches.",
        "prompt": "medieval illuminated manuscript illustration, parchment texture, rich pigments, ornate borders",
    },
    {
        "value": "renaissance",
        "label": "Renaissance Studio",
        "summary": "Oil portraits, chiaroscuro light, architectural balance.",
        "prompt": "renaissance oil painting, chiaroscuro lighting, classical architecture, detailed realism",
    },
    {
        "value": "modern",
        "label": "Modern Documentary",
        "summary": "High-contrast photography, bold geometry, contemporary palette.",
        "prompt": "modern documentary photography, bold geometric composition, high contrast lighting, cinematic color",
    },
    {
        "value": "ai_judgement",
        "label": "AI Selects Best",
        "summary": "Let the pipeline decide the most relevant style per query.",
        "prompt": "",
    },
]

_STYLE_LOOKUP = {preset["value"]: preset for preset in VISUAL_STYLE_PRESETS}


def get_visual_style_prompt(value: str | None) -> str:
    preset = _STYLE_LOOKUP.get(value or "")
    if not preset:
        return ""
    return preset.get("prompt", "")


def is_valid_visual_style(value: str | None) -> bool:
    if value is None:
        return True
    return value in _STYLE_LOOKUP


def serialize_visual_styles() -> list[dict[str, Any]]:
    return [{**preset} for preset in VISUAL_STYLE_PRESETS]
