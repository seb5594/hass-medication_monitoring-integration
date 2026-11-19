"""Check release date padding, valid dates, and the daily build counter."""

from pathlib import Path
import runpy
import unittest

validate_version = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / ".github/checks/version_scheme.py")
)["validate_version"]


class VersionSchemeTests(unittest.TestCase):
    def test_padded_dates_and_builds(self):
        for version in ("2026.02.03", "2026.02.03.1", "2026.11.19.12", "2024.02.29", "2026.11.19.0"):
            with self.subTest(version=version):
                validate_version(version)

    def test_invalid_padding_and_builds(self):
        for version in ("2026.2.03.0", "2026.02.3.0", "2026.02.3", "2026.02.03.-1",
                        "2026.02.03.01", "2026.02.03.0b1", "v2026.02.03.0"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_version(version)

    def test_invalid_dates(self):
        for version in ("2026.02.29.0", "2026.13.01.0", "2026.04.31.0", "2026.01.00.0"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_version(version)


if __name__ == "__main__":
    unittest.main()
