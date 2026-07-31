"""Pure data normalization helpers for Beszel API payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import ipaddress
import math
from typing import Any

LEGACY_RATE_TO_BYTES = 1024 * 1024
LEGACY_CONTAINER_MAX_LAG = 120


def normalize_host(value: str) -> str:
    """Return a canonical hostname or IP address without scheme or port."""
    host = value.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not host or any(char in host for char in "/?#@") or "://" in host:
        raise ValueError("host must not contain a scheme, port, path, or credentials")
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        try:
            canonical = host.rstrip(".").encode("idna").decode("ascii").lower()
        except UnicodeError as err:
            raise ValueError("invalid hostname") from err
        if not canonical or any(
            not label or len(label) > 63 for label in canonical.split(".")
        ):
            raise ValueError("invalid hostname")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
        if any(set(label) - allowed for label in canonical.split(".")):
            raise ValueError("invalid hostname")
        return canonical


def hub_unique_id(host: str, port: int, use_ssl: bool) -> str:
    """Build a stable unique ID for one Beszel endpoint."""
    normalized = normalize_host(host)
    scheme = "https" if use_ssl else "http"
    display_host = f"[{normalized}]" if ":" in normalized else normalized
    return f"{scheme}://{display_host}:{int(port)}"


def _number(value: Any) -> float | None:
    """Convert a JSON value to a finite number."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _rounded(value: Any, digits: int = 2) -> float | int | None:
    """Return a rounded finite number, keeping exact integers compact."""
    number = _number(value)
    if number is None:
        return None
    rounded = round(number, digits)
    return int(rounded) if rounded.is_integer() else rounded


def _array_number(value: Any, index: int) -> float | None:
    if not isinstance(value, (list, tuple)) or len(value) <= index:
        return None
    return _number(value[index])


def _legacy_rate(value: Any) -> float | int | None:
    """Convert legacy Beszel MiB/s-style metrics to bytes/s."""
    number = _number(value)
    return _rounded(number * LEGACY_RATE_TO_BYTES) if number is not None else None


def _temperature(info: dict[str, Any], stats: dict[str, Any]) -> float | int | None:
    dashboard = _number(info.get("dt"))
    if dashboard is not None:
        return _rounded(dashboard, 1)
    temperatures = stats.get("t")
    if isinstance(temperatures, dict):
        values = [
            number
            for value in temperatures.values()
            if (number := _number(value)) is not None
        ]
        return _rounded(max(values), 1) if values else None
    if isinstance(temperatures, (list, tuple)):
        values = [
            number for value in temperatures if (number := _number(value)) is not None
        ]
        return _rounded(max(values), 1) if values else None
    return _rounded(temperatures, 1)


def _gpu_usage(info: dict[str, Any], stats: dict[str, Any]) -> float | int | None:
    aggregate = _number(info.get("g"))
    if aggregate is not None:
        return _rounded(aggregate, 1)
    gpu_data = stats.get("g")
    if not isinstance(gpu_data, dict):
        return None
    usages = [
        number
        for gpu in gpu_data.values()
        if isinstance(gpu, dict) and (number := _number(gpu.get("u"))) is not None
    ]
    if usages:
        return _rounded(max(usages), 1)
    return 0 if any(isinstance(gpu, dict) for gpu in gpu_data.values()) else None


def normalize_extra_filesystems(stats: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize Beszel extra filesystem statistics."""
    normalized: dict[str, dict[str, Any]] = {}
    filesystems = stats.get("efs")
    if not isinstance(filesystems, dict):
        return normalized
    for name, raw in filesystems.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            continue
        total = _number(raw.get("d"))
        used = _number(raw.get("du"))
        usage = _number(raw.get("dp"))
        if usage is None and total is not None and total > 0 and used is not None:
            usage = used / total * 100
        read = _rounded(raw.get("rb")) if "rb" in raw else _legacy_rate(raw.get("r"))
        write = _rounded(raw.get("wb")) if "wb" in raw else _legacy_rate(raw.get("w"))
        if read is None and raw:
            read = 0
        if write is None and raw:
            write = 0
        normalized[name] = {
            "usage": _rounded(usage, 1),
            "total": _rounded(total),
            "used": _rounded(used),
            "read": read,
            "write": write,
        }
    return normalized


def normalize_system(
    system: dict[str, Any],
    stats: dict[str, Any],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize one current and historical system payload."""
    details = details or {}
    info = system.get("info") if isinstance(system.get("info"), dict) else {}
    load = stats.get("la", info.get("la"))
    battery = info.get("bat", stats.get("bat"))
    network = stats.get("b")
    disk_io = stats.get("dio")

    network_sent = _array_number(network, 0)
    network_received = _array_number(network, 1)
    if network_sent is None:
        network_sent = _number(_legacy_rate(stats.get("ns")))
    if network_received is None:
        network_received = _number(_legacy_rate(stats.get("nr")))
    if stats and network_sent is None:
        network_sent = 0
    if stats and network_received is None:
        network_received = 0

    disk_read = _array_number(disk_io, 0)
    disk_write = _array_number(disk_io, 1)
    if disk_read is None:
        disk_read = _number(_legacy_rate(stats.get("dr")))
    if disk_write is None:
        disk_write = _number(_legacy_rate(stats.get("dw")))
    if stats and disk_read is None:
        disk_read = 0
    if stats and disk_write is None:
        disk_write = 0

    bandwidth = _number(info.get("bb"))
    if bandwidth is None:
        bandwidth = _number(_legacy_rate(info.get("b")))
    if bandwidth is None and network_sent is not None and network_received is not None:
        bandwidth = network_sent + network_received

    cores = _number(details.get("cores"))
    if cores is None:
        cores = _number(info.get("c"))
    if cores is None and isinstance(stats.get("cpus"), list):
        cores = float(len(stats["cpus"]))

    memory_total = _number(stats.get("m"))
    if memory_total is None:
        details_memory = _number(details.get("memory"))
        if details_memory is not None:
            memory_total = details_memory / (1024**3)

    metrics = {
        "cpu": _rounded(stats.get("cpu", info.get("cpu")), 1),
        "cpu_cores": _rounded(cores, 0),
        "temperature": _temperature(info, stats),
        "memory": _rounded(stats.get("mp", info.get("mp")), 1),
        "disk": _rounded(stats.get("dp", info.get("dp")), 1),
        "disk_total": _rounded(stats.get("d")),
        "disk_used": _rounded(stats.get("du")),
        "uptime": _rounded(info.get("u"), 0),
        "bandwidth": _rounded(bandwidth),
        "load_1": _rounded(_array_number(load, 0), 2),
        "load_5": _rounded(_array_number(load, 1), 2),
        "load_15": _rounded(_array_number(load, 2), 2),
        "gpu": _gpu_usage(info, stats),
        "battery": _rounded(_array_number(battery, 0), 1),
        "disk_read": _rounded(disk_read),
        "disk_write": _rounded(disk_write),
        "network_sent": _rounded(network_sent),
        "network_received": _rounded(network_received),
        "memory_used": _rounded(stats.get("mu")),
        "memory_total": _rounded(memory_total),
        "memory_buffered": _rounded(stats.get("mb")),
        "swap_used": _rounded(stats.get("su")),
        "swap_total": _rounded(stats.get("s")),
        "ip": system.get("host"),
    }
    return {
        "id": str(system.get("id", "")),
        "name": str(system.get("name") or system.get("id") or "Beszel system"),
        "status": str(system.get("status") or "unknown").lower(),
        "host": system.get("host"),
        "port": system.get("port"),
        "updated": system.get("updated"),
        "agent_version": info.get("v"),
        "metrics": metrics,
        "filesystems": normalize_extra_filesystems(stats),
        "raw_info": info,
        "raw_stats": stats,
        "raw_details": details,
    }


def _historical_containers(
    records: list[dict[str, Any]],
    system_stats_created: dict[str, str],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Index historical container statistics by system and container name."""
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        system_id = record.get("system")
        entries = record.get("stats")
        if not isinstance(system_id, str) or not isinstance(entries, list):
            continue
        if not _record_is_current(
            record.get("created"), system_stats_created.get(system_id)
        ):
            continue
        for raw in entries:
            if not isinstance(raw, dict) or not isinstance(raw.get("n"), str):
                continue
            indexed.setdefault((system_id, raw["n"]), raw)
    return indexed


def _record_is_current(container_created: Any, system_created: Any) -> bool:
    """Return whether historical container data matches current system history."""
    if not isinstance(container_created, str) or not isinstance(system_created, str):
        return True
    try:
        container_time = datetime.fromisoformat(
            container_created.replace("Z", "+00:00")
        )
        system_time = datetime.fromisoformat(system_created.replace("Z", "+00:00"))
    except ValueError:
        return True
    if container_time.tzinfo is None:
        container_time = container_time.replace(tzinfo=timezone.utc)
    if system_time.tzinfo is None:
        system_time = system_time.replace(tzinfo=timezone.utc)
    return (
        abs((system_time - container_time).total_seconds()) <= LEGACY_CONTAINER_MAX_LAG
    )


def normalize_containers(
    current: list[dict[str, Any]],
    historical: list[dict[str, Any]],
    system_names: dict[str, str],
    *,
    system_stats_created: dict[str, str] | None = None,
    include_historical_only: bool = True,
) -> dict[str, dict[str, Any]]:
    """Merge current container state with the latest historical metrics."""
    history = _historical_containers(historical, system_stats_created or {})
    normalized: dict[str, dict[str, Any]] = {}
    seen: set[tuple[str, str]] = set()

    for state in current:
        system_id = state.get("system")
        name = state.get("name")
        record_id = state.get("id")
        if not all(
            isinstance(value, str) and value for value in (system_id, name, record_id)
        ):
            continue
        raw = history.get((system_id, name), {})
        seen.add((system_id, name))
        normalized[record_id] = _normalize_container(
            record_id, system_id, name, system_names, state, raw
        )

    if not include_historical_only:
        return normalized

    for (system_id, name), raw in history.items():
        if (system_id, name) in seen:
            continue
        digest = sha256(f"{system_id}\0{name}".encode()).hexdigest()[:12]
        record_id = f"legacy-{digest}"
        normalized[record_id] = _normalize_container(
            record_id,
            system_id,
            name,
            system_names,
            {"status": "running"},
            raw,
        )
    return normalized


def _normalize_container(
    record_id: str,
    system_id: str,
    name: str,
    system_names: dict[str, str],
    state: dict[str, Any],
    raw: dict[str, Any],
) -> dict[str, Any]:
    bandwidth = raw.get("b")
    sent = _array_number(bandwidth, 0)
    received = _array_number(bandwidth, 1)
    if sent is None:
        sent = _number(_legacy_rate(raw.get("ns")))
    if received is None:
        received = _number(_legacy_rate(raw.get("nr")))
    if sent is None and (raw or _number(state.get("net")) == 0):
        sent = 0
    if received is None and (raw or _number(state.get("net")) == 0):
        received = 0
    status = str(state.get("status") or "unknown").lower()
    return {
        "id": record_id,
        "system_id": system_id,
        "system_name": system_names.get(system_id, system_id),
        "name": name,
        "status": status,
        "running": status in {"running", "up"} or status.startswith("up "),
        "health": state.get("health"),
        "image": state.get("image"),
        "ports": state.get("ports"),
        "updated": state.get("updated"),
        "metrics": {
            "cpu": _rounded(state.get("cpu", raw.get("c")), 1),
            "memory": _rounded(state.get("memory", raw.get("m")), 2),
            "network_sent": _rounded(sent),
            "network_received": _rounded(received),
        },
    }


def normalize_smart(
    record: dict[str, Any], system_names: dict[str, str]
) -> dict[str, Any] | None:
    """Normalize one SMART record."""
    record_id = record.get("id")
    system_id = record.get("system")
    if not isinstance(record_id, str) or not isinstance(system_id, str):
        return None
    attributes: dict[int, Any] = {}
    raw_attributes = record.get("attributes")
    if isinstance(raw_attributes, list):
        for attribute in raw_attributes:
            if not isinstance(attribute, dict):
                continue
            attribute_id = _number(attribute.get("id"))
            if attribute_id is not None:
                raw_value = attribute.get("rv")
                attributes[int(attribute_id)] = (
                    raw_value if raw_value is not None else attribute.get("raw")
                )
    elif isinstance(raw_attributes, dict):
        for key, value in raw_attributes.items():
            try:
                attributes[int(key)] = value
            except (TypeError, ValueError):
                continue
    device = str(
        record.get("device") or record.get("name") or record.get("disk_id") or record_id
    )
    disk_id = device.replace("/dev/", "").replace("/", "_")
    power_on_hours = _number(record.get("hours"))
    if power_on_hours is None:
        power_on_hours = _number(attributes.get(9))
    return {
        "id": record_id,
        "system_id": system_id,
        "system_name": system_names.get(system_id, system_id),
        "disk_id": disk_id,
        "device": device,
        "model": str(record.get("model") or "SMART disk"),
        "serial": record.get("serial"),
        "firmware": record.get("firmware"),
        "disk_type": record.get("type"),
        "capacity": _rounded(record.get("capacity"), 0),
        "power_cycles": _rounded(record.get("cycles"), 0),
        "updated": record.get("updated"),
        "metrics": {
            "health": record.get("state"),
            "temperature": _rounded(record.get("temp"), 1),
            "reallocated_sectors": _rounded(attributes.get(5), 0),
            "pending_sectors": _rounded(attributes.get(197), 0),
            "uncorrectable_sectors": _rounded(attributes.get(198), 0),
            "power_on_hours": _rounded(power_on_hours, 0),
        },
        "attributes": attributes,
    }
