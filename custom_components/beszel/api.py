"""Asynchronous PocketBase API client for Beszel."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import re
from typing import Any

import aiohttp
from yarl import URL

from .const import API_CONCURRENCY, API_MAX_PAGES, API_PAGE_SIZE, API_TIMEOUT
from .models import normalize_host

_LOGGER = logging.getLogger(__name__)
_RECORD_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class BeszelAPIError(Exception):
    """Base exception for Beszel API failures."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class BeszelAuthError(BeszelAPIError):
    """Raised when Beszel rejects the configured credentials."""


@dataclass(slots=True)
class BeszelSnapshot:
    """Raw records returned by one coordinated API update."""

    systems: list[dict[str, Any]] = field(default_factory=list)
    system_details: dict[str, dict[str, Any]] = field(default_factory=dict)
    system_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    system_stats_created: dict[str, str] = field(default_factory=dict)
    containers: list[dict[str, Any]] = field(default_factory=list)
    container_stats: list[dict[str, Any]] = field(default_factory=list)
    container_mode: str = "disabled"
    smart_devices: list[dict[str, Any]] = field(default_factory=list)
    complete: dict[str, bool] = field(
        default_factory=lambda: {
            "systems": True,
            "system_details": True,
            "system_stats": True,
            "containers": True,
            "container_stats": True,
            "smart": True,
        }
    )


class BeszelAPIClient:
    """Small, authenticated client for the Beszel PocketBase API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = False,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._auth_token: str | None = None
        self._auth_lock = asyncio.Lock()
        self._request_semaphore = asyncio.Semaphore(API_CONCURRENCY)
        self._timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        self._base_url = URL.build(
            scheme="https" if use_ssl else "http",
            host=normalize_host(host),
            port=int(port),
        )

    @property
    def base_url(self) -> str:
        """Return the normalized endpoint URL."""
        return str(self._base_url).rstrip("/")

    async def authenticate(self, *, force: bool = False) -> None:
        """Authenticate and retain a valid PocketBase user token."""
        async with self._auth_lock:
            if self._auth_token and not force:
                return
            payload = {"identity": self._username, "password": self._password}
            url = self._base_url / "api/collections/users/auth-with-password"
            try:
                async with self._session.post(
                    url, json=payload, timeout=self._timeout
                ) as response:
                    data = await self._decode_json(response)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise BeszelAPIError(f"Connection to Beszel failed: {err}") from err

            if response.status in (400, 401, 403):
                self._auth_token = None
                raise BeszelAuthError(
                    "Beszel rejected the credentials", response.status
                )
            if response.status >= 400:
                self._auth_token = None
                raise BeszelAPIError(
                    self._error_message(data, response.status), response.status
                )
            token = data.get("token") if isinstance(data, dict) else None
            if not isinstance(token, str) or not token:
                self._auth_token = None
                raise BeszelAPIError("Beszel authentication returned no token")
            self._auth_token = token

    async def _refresh_after_unauthorized(self, failed_token: str | None) -> None:
        """Refresh once, avoiding a reauthentication stampede."""
        async with self._auth_lock:
            if self._auth_token and self._auth_token != failed_token:
                return
            self._auth_token = None
        await self.authenticate()

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> Any:
        await self.authenticate()
        token = self._auth_token
        headers = {"Authorization": f"Bearer {token}"}
        url = self._base_url / path.lstrip("/")
        try:
            async with self._request_semaphore:
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    timeout=self._timeout,
                ) as response:
                    data = await self._decode_json(response)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise BeszelAPIError(f"Connection to Beszel failed: {err}") from err

        if response.status == 401 and retry_auth:
            await self._refresh_after_unauthorized(token)
            return await self._request_json(
                method, path, params=params, retry_auth=False
            )
        if response.status == 401:
            raise BeszelAuthError(
                self._error_message(data, response.status), response.status
            )
        if response.status >= 400:
            raise BeszelAPIError(
                self._error_message(data, response.status), response.status
            )
        return data

    @staticmethod
    async def _decode_json(response: aiohttp.ClientResponse) -> Any:
        try:
            return await response.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError) as err:
            if response.status >= 400:
                body = (await response.text())[:200]
                return {"message": body or "Empty error response"}
            raise BeszelAPIError(
                f"Beszel returned invalid JSON (HTTP {response.status})",
                response.status,
            ) from err

    @staticmethod
    def _error_message(data: Any, status: int) -> str:
        if isinstance(data, dict):
            message = data.get("message")
            if isinstance(message, str) and message:
                return f"Beszel API error {status}: {message}"
        return f"Beszel API request failed with HTTP {status}"

    async def get_records(
        self,
        collection: str,
        *,
        filter_value: str | None = None,
        sort: str | None = None,
        per_page: int = API_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        """Return every page from a PocketBase collection."""
        records: list[dict[str, Any]] = []
        page = 1
        while True:
            if page > API_MAX_PAGES:
                raise BeszelAPIError(
                    f"Beszel collection {collection} exceeds the safe pagination limit"
                )
            params: dict[str, Any] = {"page": page, "perPage": per_page}
            if filter_value:
                params["filter"] = filter_value
            if sort:
                params["sort"] = sort
            data = await self._request_json(
                "GET", f"api/collections/{collection}/records", params=params
            )
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                raise BeszelAPIError(
                    f"Beszel returned an invalid page for collection {collection}"
                )
            if any(not isinstance(item, dict) for item in data["items"]):
                raise BeszelAPIError(
                    f"Beszel returned a malformed record in collection {collection}"
                )
            items = data["items"]
            records.extend(items)
            total_pages = data.get("totalPages")
            if isinstance(total_pages, int):
                if page >= total_pages:
                    break
            elif len(items) < per_page:
                break
            page += 1
        return records

    async def get_systems(self) -> list[dict[str, Any]]:
        """Return all systems visible to the configured user."""
        return await self.get_records("systems", sort="name")

    async def _latest_record(
        self, collection: str, system_id: str
    ) -> dict[str, Any] | None:
        if not _RECORD_ID.fullmatch(system_id):
            raise BeszelAPIError(f"Invalid system record ID: {system_id!r}")
        data = await self._request_json(
            "GET",
            f"api/collections/{collection}/records",
            params={
                "filter": f"system='{system_id}' && type='1m'",
                "sort": "-created",
                "page": 1,
                "perPage": 1,
            },
        )
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise BeszelAPIError(
                f"Beszel returned invalid latest statistics for {system_id}"
            )
        if not data["items"]:
            return None
        record = data["items"][0]
        if not isinstance(record, dict):
            raise BeszelAPIError(
                f"Beszel returned malformed latest statistics for {system_id}"
            )
        return record

    async def get_snapshot(self, *, include_docker: bool) -> BeszelSnapshot:
        """Fetch a complete, internally consistent Beszel inventory snapshot."""
        snapshot = BeszelSnapshot()
        snapshot.systems = await self.get_systems()
        system_ids: list[str] = []
        for system in snapshot.systems:
            system_id = system.get("id")
            if not isinstance(system_id, str) or not _RECORD_ID.fullmatch(system_id):
                raise BeszelAPIError("Beszel returned a system with an invalid ID")
            system_ids.append(system_id)

        async def fetch_system_history(
            system_id: str,
        ) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
            system_result, container_result = await asyncio.gather(
                self._latest_record("system_stats", system_id),
                (
                    self._latest_record("container_stats", system_id)
                    if include_docker
                    else asyncio.sleep(0, result=None)
                ),
                return_exceptions=True,
            )
            system_record: dict[str, Any] | None = None
            container_record: dict[str, Any] | None = None
            if isinstance(system_result, BeszelAuthError):
                raise system_result
            if isinstance(container_result, BeszelAuthError):
                raise container_result
            if isinstance(system_result, BeszelAPIError):
                snapshot.complete["system_stats"] = False
                _LOGGER.warning(
                    "Could not update stats for %s: %s", system_id, system_result
                )
            elif isinstance(system_result, dict):
                system_record = system_result
            elif isinstance(system_result, BaseException):
                raise system_result
            if isinstance(container_result, BeszelAPIError):
                snapshot.complete["container_stats"] = False
                _LOGGER.warning(
                    "Could not update container stats for %s: %s",
                    system_id,
                    container_result,
                )
            elif isinstance(container_result, dict):
                container_record = container_result
            elif isinstance(container_result, BaseException):
                raise container_result
            return system_id, system_record, container_record

        history = await asyncio.gather(
            *(fetch_system_history(system_id) for system_id in system_ids)
        )
        for system_id, system_record, container_record in history:
            stats = system_record.get("stats") if system_record else None
            if isinstance(stats, dict):
                snapshot.system_stats[system_id] = stats
                created = system_record.get("created")
                if isinstance(created, str):
                    snapshot.system_stats_created[system_id] = created
            elif system_record is not None:
                snapshot.complete["system_stats"] = False
                _LOGGER.warning("Ignoring malformed system stats for %s", system_id)
            if container_record:
                if isinstance(container_record.get("stats"), list):
                    snapshot.container_stats.append(container_record)
                else:
                    snapshot.complete["container_stats"] = False
                    _LOGGER.warning(
                        "Ignoring malformed container stats for %s", system_id
                    )

        details_result, containers_result, smart_result = await asyncio.gather(
            self.get_records("system_details"),
            (
                self.get_records("containers", sort="name")
                if include_docker
                else asyncio.sleep(0, result=[])
            ),
            self.get_records("smart_devices"),
            return_exceptions=True,
        )

        if isinstance(details_result, BeszelAuthError):
            raise details_result
        if isinstance(details_result, BeszelAPIError):
            if details_result.status != 404:
                snapshot.complete["system_details"] = False
            _LOGGER.debug("System details collection unavailable: %s", details_result)
        elif isinstance(details_result, list):
            for details in details_result:
                system_id = details.get("system") or details.get("id")
                if isinstance(system_id, str) and system_id:
                    snapshot.system_details[system_id] = details
                else:
                    snapshot.complete["system_details"] = False
        elif isinstance(details_result, BaseException):
            raise details_result

        if isinstance(containers_result, BeszelAuthError):
            raise containers_result
        if isinstance(containers_result, BeszelAPIError):
            if containers_result.status == 404:
                # Beszel before the live containers collection is supported through
                # its historical records.
                snapshot.container_mode = "legacy"
                snapshot.complete["containers"] = snapshot.complete["container_stats"]
            else:
                snapshot.container_mode = "error"
                snapshot.complete["containers"] = False
            _LOGGER.debug(
                "Live container collection unavailable: %s", containers_result
            )
        elif isinstance(containers_result, list):
            snapshot.container_mode = "live" if include_docker else "disabled"
            for container in containers_result:
                if all(
                    isinstance(container.get(key), str) and container[key]
                    for key in ("id", "system", "name")
                ):
                    snapshot.containers.append(container)
                else:
                    snapshot.complete["containers"] = False
        elif isinstance(containers_result, BaseException):
            raise containers_result

        if isinstance(smart_result, BeszelAuthError):
            raise smart_result
        if isinstance(smart_result, BeszelAPIError):
            if smart_result.status != 404:
                snapshot.complete["smart"] = False
            _LOGGER.debug("SMART collection unavailable: %s", smart_result)
        elif isinstance(smart_result, list):
            for device in smart_result:
                if all(
                    isinstance(device.get(key), str) and device[key]
                    for key in ("id", "system")
                ):
                    snapshot.smart_devices.append(device)
                else:
                    snapshot.complete["smart"] = False
        elif isinstance(smart_result, BaseException):
            raise smart_result

        return snapshot
