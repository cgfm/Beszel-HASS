"""Config flow for Beszel integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
        # Try to authenticate and get systems list
        auth_data = {
            "username": data[CONF_USERNAME],
            "password": data[CONF_PASSWORD]
        }
        
        async with session.post(
            f"{base_url}/api/auth/login",
            json=auth_data,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 401:
                raise InvalidAuth
            elif response.status != 200:
                raise CannotConnect
            
            # Try to get systems to verify API access
            async with session.get(
                f"{base_url}/api/systems",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as systems_response:
                if systems_response.status != 200:
                    raise CannotConnect
                
                systems = await systems_response.json()
                
    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to Beszel: %s", err)
        raise CannotConnect from err
    
    # Return info that you want to store in the config entry.
    return {
        "title": f"Beszel ({data[CONF_HOST]})",
        "systems_count": len(systems) if isinstance(systems, list) else 0
    }


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
