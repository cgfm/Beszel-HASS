"""Config flow for Beszel."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import BeszelAPIClient, BeszelAPIError, BeszelAuthError
from .const import (
    CONF_HOST,
    CONF_INCLUDE_DOCKER,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_USERNAME,
    DEFAULT_INCLUDE_DOCKER,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .models import hub_unique_id, normalize_host

_LOGGER = logging.getLogger(__name__)
_PASSWORD_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
)


def _schema(
    defaults: dict[str, Any] | None = None,
    *,
    password_required: bool = True,
) -> vol.Schema:
    values = defaults or {}
    fields: dict[Any, Any] = {
        vol.Required(CONF_HOST, default=values.get(CONF_HOST, "")): str,
        vol.Required(CONF_PORT, default=values.get(CONF_PORT, DEFAULT_PORT)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_SSL, default=values.get(CONF_SSL, DEFAULT_SSL)): bool,
        vol.Required(CONF_USERNAME, default=values.get(CONF_USERNAME, "")): str,
        vol.Required(
            CONF_INCLUDE_DOCKER,
            default=values.get(CONF_INCLUDE_DOCKER, DEFAULT_INCLUDE_DOCKER),
        ): bool,
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=values.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
        ),
    }
    password_marker = (
        vol.Required(CONF_PASSWORD)
        if password_required
        else vol.Optional(CONF_PASSWORD)
    )
    fields[password_marker] = _PASSWORD_SELECTOR
    return vol.Schema(fields)


def normalize_input(data: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize values before validation and storage."""
    normalized = dict(data)
    normalized[CONF_HOST] = normalize_host(str(data[CONF_HOST]))
    normalized[CONF_PORT] = int(data.get(CONF_PORT, DEFAULT_PORT))
    normalized[CONF_SSL] = bool(data.get(CONF_SSL, DEFAULT_SSL))
    normalized[CONF_USERNAME] = str(data[CONF_USERNAME]).strip()
    normalized[CONF_SCAN_INTERVAL] = int(
        data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    if not normalized[CONF_USERNAME] or not str(normalized[CONF_PASSWORD]):
        raise ValueError("username and password are required")
    return normalized


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Authenticate and verify access to the systems collection."""
    client = BeszelAPIClient(
        session=async_get_clientsession(hass),
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        use_ssl=data[CONF_SSL],
    )
    try:
        systems = await client.get_systems()
    except BeszelAuthError as err:
        raise InvalidAuth from err
    except BeszelAPIError as err:
        raise CannotConnect from err
    return {
        "title": f"Beszel ({client.base_url})",
        "unique_id": hub_unique_id(data[CONF_HOST], data[CONF_PORT], data[CONF_SSL]),
        "systems_count": len(systems),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Beszel config flow."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        normalized: dict[str, Any] | None = None
        if user_input is not None:
            try:
                normalized = normalize_input(user_input)
                info = await validate_input(self.hass, normalized)
            except ValueError:
                errors["base"] = "invalid_input"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error validating Beszel")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=normalized)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(normalized or user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start reauthentication after an API authorization failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update credentials and reload the existing entry."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            updated = {**entry.data, **user_input}
            try:
                normalized = normalize_input(updated)
                await validate_input(self.hass, normalized)
            except ValueError:
                errors["base"] = "invalid_input"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error reauthenticating Beszel")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: normalized[CONF_USERNAME],
                        CONF_PASSWORD: normalized[CONF_PASSWORD],
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "")
                    ): str,
                    vol.Required(CONF_PASSWORD): _PASSWORD_SELECTOR,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Edit and revalidate all Beszel settings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        normalized: dict[str, Any] | None = None
        if user_input is not None:
            try:
                submitted = {**self.config_entry.data, **user_input}
                if not user_input.get(CONF_PASSWORD):
                    submitted[CONF_PASSWORD] = self.config_entry.data[CONF_PASSWORD]
                normalized = normalize_input(submitted)
                info = await validate_input(self.hass, normalized)
                for other in self.hass.config_entries.async_entries(DOMAIN):
                    if (
                        other.entry_id != self.config_entry.entry_id
                        and other.unique_id == info["unique_id"]
                    ):
                        raise AlreadyConfigured
            except ValueError:
                errors["base"] = "invalid_input"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except AlreadyConfigured:
                errors["base"] = "already_configured"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error validating Beszel options")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=info["title"],
                    data=normalized,
                    unique_id=info["unique_id"],
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                normalized or self.config_entry.data,
                password_required=False,
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """The Beszel endpoint could not be reached or read."""


class InvalidAuth(HomeAssistantError):
    """Beszel rejected the supplied credentials."""


class AlreadyConfigured(HomeAssistantError):
    """The endpoint is already configured by another entry."""
