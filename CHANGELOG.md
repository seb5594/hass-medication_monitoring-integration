# Changelog

New versions use `YYYY.MM.DD.BUILD`: four-digit year, two-digit month and day, followed by
a non-negative build number starting at `0` for each day (for example, `2026.02.03.0`).
Release tags and titles use the version without a `v` prefix.
Existing releases retain their original version numbers.

## 2026.11.19.0

- Publish the release tag and title without a leading `v`.

- Enforce the `YYYY.MM.DD.BUILD` release format, including zero-padded months and days.

- Correct translated management, medication-type, and notification-sound selections in the options
  flow; use native selector translations and retain a fallback for older Home Assistant releases.
- Translate entity names and identify card entities by medication identity and role, so translated
  or renamed entity IDs keep the correct status, stock, and action buttons.
- Follow the dashboard user's language, including regional German tags, and preserve the literal
  `{stock}` example in the low-stock template editor.

- Detect Medication Tracker profiles from the original project and previous fork during setup,
  including active profiles and saved stores left behind after uninstalling the old integration.
- Preview medications before importing; disable a running source only after confirmation to
  prevent duplicate reminders. Keep source data for rollback and prevent duplicate imports.
- Validate imported stores and refuse to copy sources that failed to unload. Preserve the new
  tracker's data on reload; the old integration does not need to remain installed.
- Update installation and metadata links to the renamed Medication Monitoring repository.

## 2026.11.17.0

- Support Home Assistant Core from 2021.12.10, including the button and stock-control entities.
- Give the Community edition a distinct Home Assistant domain and HACS package for a separate catalog listing.
- Add an optional import from a disabled legacy tracker for medication schedules, dose history, stock, and notification preferences.
- See the [upgrade steps](README.md#upgrade-from-the-previous-fork-release-or-import-from-upstream) for existing dashboards and automations.

## 2026.11.16.0

- Add the Health & wellbeing Marketplace category.
- Include the existing MIT license and attribution in the HACS installation ZIP.

## 2026.10.31.0

- Notification titles, messages, and the mobile **Mark taken** action now follow
  the Home Assistant system language, with German translations for due, overdue,
  due-soon, taken, and low-stock alerts and English as the fallback.
- Previously saved default message templates are localized automatically; custom
  templates are preserved, and the options flow shows the localized defaults.

## 2026.10.20.0

- German translation of the setup and options dialogs. The integration is called
  "Medikamentenübersicht" in German.
- The Lovelace card follows the language of the Home Assistant user profile (English and German);
  other languages fall back to English.
- The Lovelace card is served by the integration and loaded into the frontend automatically.
  The file in `config/www` and the dashboard resource are no longer needed and can be removed.
- Requires Home Assistant 2024.7 or newer (`async_register_static_paths`).
- The brand icon is a real PNG now, with an `@2x` variant.
- Releases are built and published as a ZIP by the shared workflow engine.
