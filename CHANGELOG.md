# Changelog

## 1.3.0

- Identified Docker and Podman containers by their monitored system and container
  name instead of the runtime container ID, which Beszel reports per poll and
  Docker replaces on every image update, `compose up` or redeploy.
  - A recreated container now keeps its entity, its device and its long-term
    statistics instead of gaining a `_2` entity whose predecessor is retired,
    which left the retired entity's statistics orphaned in the Recorder (reported
    by Spook as "orphaned long-term statistics") and re-orphaned the other series
    on the next recreate.
  - A recreate no longer registers a second entity for a container: the retired
    and the fresh record now collapse onto one identity.
- Migrated existing container entities, devices and unique IDs to the new identity
  on setup, keeping each entity ID and each device's area, name and labels.
- Container sensors expose the stable identity as a new `key` attribute;
  `container_id` keeps reporting the current runtime container ID.

## 1.2.1

- Grouped SMART disk entities under their corresponding monitored system again
  instead of exposing every disk as a separate device.

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
