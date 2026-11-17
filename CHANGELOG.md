# Changelog

Versions follow the scheme of the original project: `YYYY.M.D.B`, the release date plus a build
number for the day.

## 2026.11.17.0

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
