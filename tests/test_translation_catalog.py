"""Guard catalog assignment and placeholders against untranslated UI regressions."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/medication_monitoring"


class TranslationCatalogTests(unittest.TestCase):
    def test_english_source_matches_english_catalog(self):
        self.assertEqual(
            json.loads((ROOT / "strings.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8")),
        )

    def test_selectors_entities_and_placeholders_match_between_languages(self):
        en = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))
        de = json.loads((ROOT / "translations/de.json").read_text(encoding="utf-8"))

        def leaves(value, prefix=""):
            result = {}
            for key, item in value.items():
                path = f"{prefix}.{key}"
                if isinstance(item, dict):
                    result.update(leaves(item, path))
                else:
                    result[path] = item
            return result

        for section in ("selector", "entity", "options", "config"):
            english, german = leaves(en[section]), leaves(de[section])
            self.assertEqual(english.keys(), german.keys(), section)
            for key in english:
                self.assertEqual(set(re.findall(r"\{\w+\}", english[key])),
                                 set(re.findall(r"\{\w+\}", german[key])), key)


if __name__ == "__main__":
    unittest.main()
