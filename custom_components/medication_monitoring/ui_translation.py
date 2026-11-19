"""Translated option selectors with a fallback for older Home Assistant cores."""

from functools import lru_cache
import json
from pathlib import Path

from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig


@lru_cache(maxsize=2)
def _labels(language):
    path = Path(__file__).parent / "translations" / f"{language}.json"
    return json.loads(path.read_text(encoding="utf-8"))["selector"]


async def async_select(hass, context, key, options):
    """Let modern frontends use the user's language; retain labels on old cores."""
    if "translation_key" in SelectSelectorConfig.__annotations__:
        return SelectSelector({"options": list(options), "translation_key": key})
    tag = context.get("language") or getattr(hass.config, "language", None) or "en"
    language = "de" if tag.lower().replace("_", "-").split("-")[0] == "de" else "en"
    labels = await hass.async_add_executor_job(_labels, language)
    return SelectSelector({"options": [
        {"value": value, "label": labels[key]["options"].get(value, fallback)}
        for value, fallback in options.items()
    ]})
