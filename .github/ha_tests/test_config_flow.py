"""Open the integration via the same config-flow manager as the UI."""

from datetime import date
from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.data_entry_flow import FlowResultType


async def test_user_can_open_medication_setup(hass):
    result = await hass.config_entries.flow.async_init(
        "medication_monitoring", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "title" in result["data_schema"].schema
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_import_disabled_tracker_once(hass, monkeypatch):
    """Copy the legacy profile via the same setup flow used by existing users."""
    domain = "medication_monitoring"
    monkeypatch.setattr(
        "custom_components.medication_monitoring.async_register_card", AsyncMock()
    )
    active = MockConfigEntry(domain="medication_tracker", title="Active")
    legacy = MockConfigEntry(
        domain="medication_tracker",
        title="Old tracker",
        disabled_by=config_entries.ConfigEntryDisabler.USER,
    )
    active.add_to_hass(hass)
    legacy.add_to_hass(hass)
    original = {
        "medications": [
            {"id": "test_med", "name": "Test medication", "times": ["08:00"], "current_stock": 5}
        ],
        "dose_log": {"test_med": [{"date": date.today().isoformat(), "status": "taken"}]},
        "notifications": {"due_enabled": False},
    }
    legacy_store = Store(hass, 1, f"medication_tracker_data_{legacy.entry_id}")
    await legacy_store.async_save(original)

    result = await hass.config_entries.flow.async_init(
        domain, context={"source": config_entries.SOURCE_USER}
    )
    source_field = result["data_schema"].schema["legacy_entry_id"]
    assert source_field.container == {legacy.entry_id: legacy.title}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"legacy_entry_id": legacy.entry_id}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.title == legacy.title
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.LOADED

    new_store = Store(hass, 1, f"{domain}_data_{entry.entry_id}")
    assert await new_store.async_load() == original
    await legacy_store.async_save({**original, "medications": []})
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert await new_store.async_load() == original
