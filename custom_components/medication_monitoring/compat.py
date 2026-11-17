"""Home Assistant APIs that differ across supported Core versions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import MedicationCoordinator

try:
    from homeassistant.helpers.device_registry import DeviceInfo
except ImportError:
    from homeassistant.helpers.entity import DeviceInfo


def set_coordinator(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: MedicationCoordinator
) -> None:
    """Store the coordinator for this config entry until unload."""
    coordinators = hass.data.setdefault(DOMAIN, {})
    coordinators[entry.entry_id] = coordinator
    @callback
    def remove_coordinator() -> None:
        coordinators.pop(entry.entry_id, None)

    entry.async_on_unload(remove_coordinator)


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> MedicationCoordinator | None:
    """Return the loaded coordinator for an entry, including older Core releases."""
    return hass.data.get(DOMAIN, {}).get(entry.entry_id)


def entity_name(medication_name: str, name: str) -> str:
    """Prefix names on Core releases that do not derive them from devices."""
    if hasattr(Entity, "has_entity_name"):
        return name
    return f"{medication_name} {name}"
