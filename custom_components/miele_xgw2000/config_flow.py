"""Config flow for Miele XGW 2000."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.data_entry_flow import FlowResult

from .api import MieleApi, MieleApiError
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
)

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


# hassfest accepts no URLs in strings.json, so the endpoint goes in here
STATS_PLACEHOLDERS = {"endpoint": "stats.rnet.se"}

# Same key as stats.OPTION_KEY. Not imported from there: stats.py pulls in
# more of Home Assistant than the config flow needs.
CONF_SEND_STATISTICS = "send_statistics"


class MieleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MieleOptionsFlow()

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            username = user_input.get(CONF_USERNAME, "").strip() or None
            password = user_input.get(CONF_PASSWORD, "").strip() or None
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            api = MieleApi(host, username, password)
            try:
                await api.get_appliances()
            except MieleApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Miele XGW 2000 ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username or "",
                        CONF_PASSWORD: password or "",
                        CONF_SCAN_INTERVAL: scan_interval,
                    },
                )
            finally:
                await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )


class MieleOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            was_on = self.config_entry.options.get(CONF_SEND_STATISTICS, True)
            if was_on and not user_input.get(CONF_SEND_STATISTICS, True):
                # The server marks the installation as opted out
                from .stats import async_forget_install

                await async_forget_install(self.hass, self.config_entry, DOMAIN)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SEND_STATISTICS,
                        default=self.config_entry.options.get(CONF_SEND_STATISTICS, True),
                    ): cv.boolean,
                }
            ),
            description_placeholders=STATS_PLACEHOLDERS,
        )
