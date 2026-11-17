"""Storage discovery and validation without requiring Home Assistant."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components/medication_monitoring"
PACKAGE = "_medication_legacy_tests"
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package


def load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("const")
storage = ModuleType("homeassistant.helpers.storage")
storage.Store = Mock()
core = ModuleType("homeassistant.core")
core.HomeAssistant = Mock
exceptions = ModuleType("homeassistant.exceptions")
exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
with patch.dict(sys.modules, {
    "homeassistant": ModuleType("homeassistant"), "homeassistant.core": core,
    "homeassistant.exceptions": exceptions,
    "homeassistant.helpers": ModuleType("homeassistant.helpers"),
    "homeassistant.helpers.storage": storage,
}):
    legacy = load("legacy")


class LegacyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original = {
            "medications": [{"id": "med1", "name": "Medication", "times": ["08:00"]}],
            "dose_log": {"med1": [{"date": "2026-11-17", "action": "taken"}]},
            "notifications": {"due_enabled": True},
        }
        self.store = SimpleNamespace(async_load=AsyncMock(return_value=self.original))
        self.hass = SimpleNamespace(config_entries=Mock())
        self.hass.config_entries.async_get_entry.return_value = None
        self.patch_store = patch.object(legacy, "Store", return_value=self.store)
        self.patch_store.start()
        self.addCleanup(self.patch_store.stop)

    def test_only_complete_legacy_store_names_are_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("medication_tracker_data_123", "medication_tracker_data_ABC-def",
                         "medication_tracker_data_123.backup", "medication_monitoring_data_123"):
                (Path(directory) / name).touch()
            self.assertEqual(legacy._stored_entry_ids(directory), ["123", "ABC-def"])

    async def test_removed_source_is_read_as_an_independent_copy(self):
        copied = await legacy.async_load_legacy_data(self.hass, "old123")
        self.assertEqual(copied, self.original)
        copied["medications"][0]["name"] = "Changed"
        self.assertEqual(self.original["medications"][0]["name"], "Medication")

    async def test_active_and_failed_unload_sources_cannot_be_copied(self):
        for disabled, state in ((None, "loaded"), ("user", "failed_unload"), ("user", "loaded")):
            self.hass.config_entries.async_get_entry.return_value = SimpleNamespace(
                domain="medication_tracker", disabled_by=disabled, state=state
            )
            self.assertIsNone(await legacy.async_load_legacy_data(self.hass, "old123"))
            self.assertEqual(await legacy.async_load_legacy_data(
                self.hass, "old123", allow_active=True
            ), self.original)

    async def test_invalid_or_duplicate_data_is_rejected(self):
        duplicate = deepcopy(self.original)
        duplicate["medications"].append(deepcopy(duplicate["medications"][0]))
        for invalid in (None, {}, {"medications": [None]}, duplicate,
                        {**self.original, "dose_log": {"med1": [None]}},
                        {**self.original, "notifications": []}):
            self.store.async_load.return_value = invalid
            self.assertIsNone(await legacy.async_load_legacy_data(self.hass, "old123"))

    async def test_foreign_domain_and_path_components_are_rejected(self):
        self.assertIsNone(await legacy.async_load_legacy_data(self.hass, "../core.config_entries"))
        self.hass.config_entries.async_get_entry.return_value = SimpleNamespace(domain="other")
        self.assertIsNone(await legacy.async_load_legacy_data(self.hass, "old123"))


if __name__ == "__main__":
    unittest.main()
