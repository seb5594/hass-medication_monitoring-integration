"""Medication Monitoring integration for Home Assistant."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .card import async_register_card
from .compat import get_coordinator, set_coordinator
from .const import (
    ATTR_AMOUNT,
    ATTR_MEDICATION_ID,
    ATTR_SCHEDULED_TIME,
    ATTR_TAKEN_AT,
    CONF_LEGACY_ENTRY_ID,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADJUST_STOCK,
    SERVICE_MARK_SKIPPED,
    SERVICE_MARK_TAKEN,
    SERVICE_RESET_TODAY,
)
from .coordinator import MedicationCoordinator
from .notify import MedicationNotifier

_LOGGER = logging.getLogger(__name__)

try:
    from homeassistant.exceptions import ServiceValidationError
except ImportError:
    from homeassistant.exceptions import HomeAssistantError as ServiceValidationError

if hasattr(cv, "config_entry_only_config_schema"):
    CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
else:
    CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema({})}, extra=vol.ALLOW_EXTRA)

# ---------------------------------------------------------------------------
# Service schemas
# ---------------------------------------------------------------------------

_SERVICE_BASE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

_MARK_TAKEN_SCHEMA = _SERVICE_BASE_SCHEMA.extend(
    {
        vol.Optional(ATTR_SCHEDULED_TIME): cv.string,
        vol.Optional(ATTR_TAKEN_AT): cv.string,
    }
)

_MARK_SKIPPED_SCHEMA = _SERVICE_BASE_SCHEMA.extend(
    {
        vol.Optional(ATTR_SCHEDULED_TIME): cv.string,
    }
)

_ADJUST_STOCK_SCHEMA = _SERVICE_BASE_SCHEMA.extend(
    {
        vol.Required(ATTR_AMOUNT): vol.All(
            vol.Coerce(float), vol.Range(min=-100000, max=100000)
        ),
    }
)

# ---------------------------------------------------------------------------
# Setup / teardown
# ---------------------------------------------------------------------------


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the Lovelace card once per Home Assistant start."""
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Medication Monitoring from a config entry."""
    coordinator = MedicationCoordinator(hass, entry.entry_id)
    await coordinator.async_load(entry.data.get(CONF_LEGACY_ENTRY_ID))

    notifier = MedicationNotifier(hass, coordinator)
    coordinator._notifier = notifier

    await coordinator.async_config_entry_first_refresh()

    set_coordinator(hass, entry, coordinator)

    manager = hass.config_entries
    if hasattr(manager, "async_forward_entry_setups"):
        await manager.async_forward_entry_setups(entry, PLATFORMS)
    else:
        # Awaiting the old API in entry setup can deadlock during component startup.
        for platform in PLATFORMS:
            hass.async_create_task(manager.async_forward_entry_setup(entry, platform))

    _register_services(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = get_coordinator(hass, entry)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and coordinator is not None and coordinator._notifier is not None:
        coordinator._notifier.unsubscribe()

    remaining = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id
    ]
    if not remaining:
        for svc in (
            SERVICE_MARK_TAKEN,
            SERVICE_MARK_SKIPPED,
            SERVICE_RESET_TODAY,
            SERVICE_ADJUST_STOCK,
        ):
            if hass.services.has_service(DOMAIN, svc):
                hass.services.async_remove(DOMAIN, svc)

    return unload_ok

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


def _get_coordinator(hass: HomeAssistant, med_id: str) -> MedicationCoordinator:
    """Find the coordinator that owns this medication id."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = get_coordinator(hass, entry)
        if coordinator is not None and coordinator.get_medication(med_id):
            return coordinator
    raise ServiceValidationError(
        f"Medication with id '{med_id}' not found in any Medication Monitoring entry."
    )


def _register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register HA services (idempotent — only registers once)."""
    if hass.services.has_service(DOMAIN, SERVICE_MARK_TAKEN):
        return

    async def handle_mark_taken(call: ServiceCall) -> None:
        med_id: str = call.data[ATTR_MEDICATION_ID]
        scheduled_time: str | None = call.data.get(ATTR_SCHEDULED_TIME)
        taken_at_raw: str | None = call.data.get(ATTR_TAKEN_AT)
        taken_at = None
        if taken_at_raw:
            from homeassistant.util.dt import parse_datetime
            taken_at = parse_datetime(taken_at_raw)
        coordinator = _get_coordinator(hass, med_id)
        success = await coordinator.async_mark_taken(
            med_id, taken_at=taken_at, scheduled_time=scheduled_time
        )
        if not success:
            raise ServiceValidationError(f"Could not mark medication '{med_id}' as taken.")

    async def handle_mark_skipped(call: ServiceCall) -> None:
        med_id: str = call.data[ATTR_MEDICATION_ID]
        scheduled_time: str | None = call.data.get(ATTR_SCHEDULED_TIME)
        coordinator = _get_coordinator(hass, med_id)
        success = await coordinator.async_mark_skipped(med_id, scheduled_time=scheduled_time)
        if not success:
            raise ServiceValidationError(f"Could not mark medication '{med_id}' as skipped.")

    async def handle_reset_today(call: ServiceCall) -> None:
        med_id: str = call.data[ATTR_MEDICATION_ID]
        coordinator = _get_coordinator(hass, med_id)
        success = await coordinator.async_reset_today(med_id)
        if not success:
            raise ServiceValidationError(
                f"Could not reset today's log for medication '{med_id}'."
            )

    async def handle_adjust_stock(call: ServiceCall) -> None:
        med_id: str = call.data[ATTR_MEDICATION_ID]
        amount: float = call.data[ATTR_AMOUNT]
        coordinator = _get_coordinator(hass, med_id)
        success = await coordinator.async_adjust_stock(med_id, amount)
        if not success:
            raise ServiceValidationError(
                f"Could not adjust stock for medication '{med_id}'. "
                "Stock tracking may not be enabled for this medication."
            )

    hass.services.async_register(
        DOMAIN, SERVICE_MARK_TAKEN, handle_mark_taken, schema=_MARK_TAKEN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_MARK_SKIPPED, handle_mark_skipped, schema=_MARK_SKIPPED_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_TODAY, handle_reset_today, schema=_SERVICE_BASE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADJUST_STOCK, handle_adjust_stock, schema=_ADJUST_STOCK_SCHEMA
    )
