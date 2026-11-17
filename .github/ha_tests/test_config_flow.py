"""Open the integration via the same config-flow manager as the UI."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_user_can_open_medication_setup(hass):
    result = await hass.config_entries.flow.async_init(
        "medication_monitoring", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
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
        disabled_by=(config_entries.ConfigEntryDisabler.USER
                     if hasattr(config_entries, "ConfigEntryDisabler") else "user"),
    )
    active.add_to_hass(hass)
    legacy.add_to_hass(hass)
    now = datetime.now(timezone.utc)
    original = {
        "medications": [
            {
                "id": "test_med", "name": "Test medication", "times": ["08:00"],
                "current_stock": 5, "stock_tracking_enabled": True,
            }
        ],
        "dose_log": {
            "test_med": [{
                "date": now.date().isoformat(), "action": "taken",
                "taken_at": now.isoformat(), "scheduled_time": "08:00",
            }]
        },
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
    assert result["step_id"] == "legacy_confirm"
    assert result["description_placeholders"]["count"] == "1"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.title == legacy.title
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.LOADED

    storage_key = f"{domain}_data_{entry.entry_id}"
    new_store = Store(hass, 1, storage_key)
    assert await new_store.async_load() == original
    assert await legacy_store.async_load() == original
    await legacy_store.async_save({**original, "medications": []})
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert await new_store.async_load() == original

    options = await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"] == "form"
    hass.config_entries.options.async_abort(options["flow_id"])

    stock_entity = "number.test_medication_stock"
    assert float(hass.states.get(stock_entity).state) == 5
    await hass.services.async_call(
        "number", "set_value", {"entity_id": stock_entity, "value": 8}, blocking=True
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.test_medication_mark_taken"}, blocking=True
    )
    assert float(hass.states.get(stock_entity).state) == 7
    saved = await Store(hass, 1, storage_key).async_load()
    assert len(saved["dose_log"]["test_med"]) == 2

    # An imported source cannot create another copy, even if its title changes.
    result = await hass.config_entries.flow.async_init(
        domain, context={"source": config_entries.SOURCE_USER}
    )
    assert "legacy_entry_id" not in result["data_schema"].schema
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_active_tracker_is_stopped_only_after_confirmation(hass, monkeypatch):
    """Selecting or cancelling a migration must not interrupt existing reminders."""
    monkeypatch.setattr("custom_components.medication_monitoring.async_register_card", AsyncMock())
    legacy = MockConfigEntry(domain="medication_tracker", title="Current tracker")
    legacy.add_to_hass(hass)
    original = {"medications": [{"id": "one", "name": "Original", "times": ["09:00"]}]}
    store = Store(hass, 1, f"medication_tracker_data_{legacy.entry_id}")
    await store.async_save(original)
    result = await hass.config_entries.flow.async_init(
        "medication_monitoring", context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"legacy_entry_id": legacy.entry_id}
    )
    assert result["step_id"] == "legacy_confirm"
    assert legacy.disabled_by is None
    hass.config_entries.flow.async_abort(result["flow_id"])
    assert legacy.disabled_by is None

    # Simulate a running source's successful unload; the real manager still sets disabled_by.
    monkeypatch.setattr(hass.config_entries, "async_reload", AsyncMock(return_value=True))
    result = await hass.config_entries.flow.async_init(
        "medication_monitoring", context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"legacy_entry_id": legacy.entry_id}
    )
    # Pick up changes made while the preview was open.
    original["medications"][0]["name"] = "Updated"
    await store.async_save(original)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert legacy.disabled_by is not None
    await hass.async_block_till_done()
    copied = await Store(hass, 1, f"medication_monitoring_data_{result['result'].entry_id}").async_load()
    assert copied == original
    assert await store.async_load() == original


async def test_import_remaining_store_without_original_integration(hass, monkeypatch):
    monkeypatch.setattr("custom_components.medication_monitoring.async_register_card", AsyncMock())
    monkeypatch.setattr(
        "custom_components.medication_monitoring.legacy._stored_entry_ids",
        lambda _: ["removed_profile"],
    )
    original = {"medications": [{"id": "one", "name": "Recovered", "times": []}]}
    await Store(hass, 1, "medication_tracker_data_removed_profile").async_save(original)
    result = await hass.config_entries.flow.async_init(
        "medication_monitoring", context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"legacy_entry_id": "removed_profile"}
    )
    assert result["step_id"] == "legacy_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert result["result"].state is config_entries.ConfigEntryState.LOADED
    copied = await Store(hass, 1, f"medication_monitoring_data_{result['result'].entry_id}").async_load()
    assert copied == original


async def test_failed_unload_does_not_create_a_tracker(hass, monkeypatch):
    legacy = MockConfigEntry(domain="medication_tracker", title="Cannot stop")
    legacy.add_to_hass(hass)
    await Store(hass, 1, f"medication_tracker_data_{legacy.entry_id}").async_save({"medications": []})
    monkeypatch.setattr(hass.config_entries, "async_set_disabled_by", AsyncMock(return_value=False))
    result = await hass.config_entries.flow.async_init(
        "medication_monitoring", context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"legacy_entry_id": legacy.entry_id}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "legacy_disable_failed"}
    assert not hass.config_entries.async_entries("medication_monitoring")
    hass.config_entries.flow.async_abort(result["flow_id"])
