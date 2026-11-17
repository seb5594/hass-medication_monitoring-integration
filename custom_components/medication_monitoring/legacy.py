"""Discover and read Medication Tracker profiles without changing their data."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import CONF_LEGACY_ENTRY_ID, DOMAIN, LEGACY_DOMAIN, LEGACY_STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)
_ENTRY_ID = re.compile(r"[a-zA-Z0-9_-]+")


@dataclass
class LegacySource:
    """A registered tracker or a remaining store from a removed integration."""

    entry_id: str
    title: str
    medications: list[str]


def _stored_entry_ids(directory: str) -> list[str]:
    """List only legacy store names; run filesystem access in the executor."""
    prefix = f"{LEGACY_STORAGE_KEY}_"
    return sorted(
        path.name[len(prefix):]
        for path in Path(directory).glob(f"{prefix}*")
        if path.is_file() and _ENTRY_ID.fullmatch(path.name[len(prefix):])
    )


async def async_load_legacy_data(
    hass: HomeAssistant, entry_id: str, *, allow_active: bool = False
) -> dict[str, Any] | None:
    """Read a validated copy from either edition's old per-entry storage key.

    Active sources can be previewed, but setup must only copy a stopped source.
    A removed config entry is allowed when its store still exists.
    """
    if not _ENTRY_ID.fullmatch(entry_id):
        return None
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is not None and (
        entry.domain != LEGACY_DOMAIN or (entry.disabled_by is None and not allow_active)
    ):
        return None
    if entry is not None and not allow_active and getattr(entry.state, "value", entry.state) in (
        "loaded", "failed_unload", "setup_in_progress", "unload_in_progress"
    ):
        return None
    try:
        data = await Store(hass, STORAGE_VERSION, f"{LEGACY_STORAGE_KEY}_{entry_id}").async_load()
    except (HomeAssistantError, OSError, ValueError):
        _LOGGER.warning("Could not read a legacy Medication Tracker store")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("medications"), list):
        return None
    ids: set[str] = set()
    for med in data["medications"]:
        if (
            not isinstance(med, dict)
            or not isinstance(med.get("id"), str) or not med["id"]
            or not isinstance(med.get("name"), str) or not med["name"].strip()
            or med["id"] in ids
        ):
            return None
        ids.add(med["id"])
    log = data.get("dose_log", {})
    if not isinstance(log, dict) or not isinstance(data.get("notifications", {}), dict):
        return None
    if any(
        not isinstance(entries, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("date", ""), str)
            for item in entries
        )
        for entries in log.values()
    ):
        return None
    return deepcopy(data)


async def async_find_legacy_sources(hass: HomeAssistant) -> dict[str, LegacySource]:
    """Find readable, not-yet-imported trackers from the fork and original."""
    imported = {
        entry.data.get(CONF_LEGACY_ENTRY_ID)
        for entry in hass.config_entries.async_entries(DOMAIN)
    }
    entries = {
        entry.entry_id: entry
        for entry in hass.config_entries.async_entries(LEGACY_DOMAIN)
    }
    stored_ids = await hass.async_add_executor_job(_stored_entry_ids, hass.config.path(".storage"))
    sources = {}
    for entry_id in sorted(set(entries) | set(stored_ids)):
        if entry_id in imported:
            continue
        data = await async_load_legacy_data(hass, entry_id, allow_active=True)
        if data is None:
            continue
        names = [med["name"] for med in data["medications"]]
        entry = entries.get(entry_id)
        title = entry.title if entry else ", ".join(names[:3]) or "Medication Tracker"
        sources[entry_id] = LegacySource(entry_id, title, names)
    return sources
