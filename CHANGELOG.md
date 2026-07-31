# Changelog

## 1.2.0

- Rebuilt API authentication, bounded concurrency, pagination, validation, and
  one-time token refresh.
- Added current Beszel container records with stable IDs and real running status,
  while retaining legacy historical-record compatibility.
- Corrected current and legacy units for system/container network and disk rates,
  container memory, temperature maps, batteries, and extra filesystems.
- Added support for Beszel's `system_details` collection while retaining the
  legacy inline system-info fallback.
- Updated SMART parsing for Beszel's current record fields and preserved valid
  zero-valued metrics when current payloads omit zero-rate fields.
- Added dynamic entity discovery and delayed, exact stale-entity cleanup.
- Scoped entity and device identities to the configured Hub and migrated known v1.1
  entity unique IDs.
- Added config-entry deduplication, reauthentication, configurable polling, English
  and German translations, masked password inputs, tests, CI validation, and a
  working release archive.
