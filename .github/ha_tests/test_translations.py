"""Exercise selector translations and entity identity through real HA setup."""

from unittest.mock import AsyncMock

from homeassistant.helpers.storage import Store
from homeassistant.helpers.selector import SelectSelectorConfig
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def prepare(hass, monkeypatch):
    monkeypatch.setattr("custom_components.medication_monitoring.async_register_card", AsyncMock())
    hass.config.language = "de"
    entry = MockConfigEntry(domain="medication_monitoring", title="Test")
    entry.add_to_hass(hass)
    await Store(hass, 1, f"medication_monitoring_data_{entry.entry_id}").async_save({
        "medications": [{"id": "vitamin", "name": "Vitamin D", "times": [],
                         "stock_tracking_enabled": True, "current_stock": 10}],
        "notifications": {"due_enabled": False},
    })
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def assert_selector(result, field, key, value, label):
    selector = result["data_schema"].schema[field]
    assert selector(value) == value
    if "translation_key" in SelectSelectorConfig.__annotations__:
        assert selector.config["translation_key"] == key
        assert value in selector.config["options"]
    else:
        assert {item["value"]: item["label"] for item in selector.config["options"]}[value] == label


async def test_management_and_sound_options_have_translation_keys(hass, monkeypatch):
    entry = await prepare(hass, monkeypatch)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert_selector(result, "action", "manage_action", "edit", "Medikament bearbeiten")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"action": "edit"})
    assert result["step_id"] == "select_medication"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"medication_id": "vitamin"})
    assert_selector(result, "med_type", "med_type", "as_needed", "Bei Bedarf")
    hass.config_entries.options.async_abort(result["flow_id"])

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"action": "notifications"})
    assert_selector(result, "action", "notification_action", "save", "Speichern und zurück")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"action": "edit_due_message"})
    assert_selector(result, "due_ios_sound_mode", "ios_sound_mode", "none", "Kein Ton")
    assert_selector(result, "due_android_importance", "android_importance", "high", "Hoch")
    hass.config_entries.options.async_abort(result["flow_id"])


async def test_entities_expose_language_independent_roles_and_german_names(hass, monkeypatch):
    entry = await prepare(hass, monkeypatch)
    states = [state for state in hass.states.async_all()
              if state.attributes.get("tracker_entry_id") == entry.entry_id]
    assert states
    by_role = {state.attributes["medication_role"]: state for state in states}
    assert {"next_dose", "last_taken", "streak", "taken_today", "stock",
            "stock_number", "mark_taken", "mark_skipped", "overdue", "due_soon", "low_stock"} <= by_role.keys()
    assert all(state.attributes["medication_name"] == "Vitamin D" for state in states)
    # Older HA does not support translated entity names; the card still uses the stable roles.
    from homeassistant.const import __version__
    if tuple(int(part) for part in __version__.split(".")[:2]) >= (2023, 6):
        assert "Nächste Einnahme" in by_role["next_dose"].attributes["friendly_name"]
        assert "Als eingenommen markieren" in by_role["mark_taken"].attributes["friendly_name"]
