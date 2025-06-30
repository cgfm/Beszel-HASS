"""Config flow for Beszel integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import CONF_SSL, DEFAULT_PORT, DEFAULT_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): bool,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    scheme = "https" if data[CONF_SSL] else "http"
    base_url = f"{scheme}://{data[CONF_HOST]}:{data[CONF_PORT]}"

    session = async_get_clientsession(hass)

    try:
        # Test basic connectivity
        _LOGGER.debug("Testing connectivity to %s", base_url)
        async with session.get(
            base_url, timeout=aiohttp.ClientTimeout(total=10)
        ) as root_response:
            if root_response.status not in [200, 401, 403, 404]:
                _LOGGER.error(
                    "Cannot reach Beszel at %s, status: %s",
                    base_url,
                    root_response.status,
                )
                raise CannotConnect

        # Try PocketBase authentication
        auth_data = {"identity": data[CONF_USERNAME], "password": data[CONF_PASSWORD]}

        # Try different user collections
        auth_collections = ["users", "_superusers"]
        auth_success = False
        token = None

        for collection in auth_collections:
            try:
                auth_endpoint = (
                    f"{base_url}/api/collections/{collection}/auth-with-password"
                )
                _LOGGER.debug("Trying auth with collection: %s", collection)

                async with session.post(
                    auth_endpoint,
                    json=auth_data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        auth_result = await response.json()
                        token = auth_result.get("token")
                        if token:
                            _LOGGER.debug(
                                "Authentication successful with collection: %s",
                                collection,
                            )
                            auth_success = True
                            break
                    elif response.status == 400:
                        error_data = await response.json()
                        _LOGGER.debug(
                            "Bad request for collection %s: %s", collection, error_data
                        )
                        if "Invalid login credentials" in str(error_data):
                            raise InvalidAuth
                    elif response.status == 404:
                        _LOGGER.debug("Collection %s not found", collection)
                        continue
                    else:
                        _LOGGER.debug(
                            "Auth failed for collection %s, status: %s",
                            collection,
                            response.status,
                        )
            except aiohttp.ClientError as err:
                _LOGGER.debug("Auth error for collection %s: %s", collection, err)
                continue

        if not auth_success:
            _LOGGER.error("Authentication failed with all collections")
            raise InvalidAuth

        # Try to get systems to verify API access
        headers = {"Authorization": f"Bearer {token}"}
        systems_endpoint = f"{base_url}/api/collections/systems/records"

        async with session.get(
            systems_endpoint, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as systems_response:
            if systems_response.status == 200:
                systems_data = await systems_response.json()
                systems = systems_data.get("items", [])
                _LOGGER.debug("Found %d systems", len(systems))
            elif systems_response.status == 403:
                _LOGGER.error("Access denied to systems collection")
                raise CannotConnect
            else:
                _LOGGER.error("Cannot get systems, status: %s", systems_response.status)
                raise CannotConnect

    except aiohttp.ClientConnectorError as err:
        _LOGGER.error("Cannot connect to %s: %s", base_url, err)
        raise CannotConnect from err
    except aiohttp.ClientTimeout as err:
        _LOGGER.error("Timeout connecting to %s: %s", base_url, err)
        raise CannotConnect from err
    except InvalidAuth:
        raise
    except Exception as err:
        _LOGGER.error("Unexpected error connecting to Beszel: %s", err)
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {"title": f"Beszel ({data[CONF_HOST]})", "systems_count": len(systems)}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Beszel."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
