"""Config flow for UDK-04-10 Dimmer (RS-485/DMX).

Design:
  - One config entry represents the RS-485 bus (port + baudrate).
  - Modules (address + names) are stored in the entry OPTIONS.
  - Each module always creates 4 dimmer channel entities.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_ADDRESS,
    CONF_BAUDRATE,
    CONF_CH1_NAME,
    CONF_CH2_NAME,
    CONF_CH3_NAME,
    CONF_CH4_NAME,
    CONF_MODULES,
    CONF_MODULE_NAME,
    CONF_PORT,
    DEFAULT_BAUDRATE,
    DEFAULT_PORT,
    DOMAIN,
)


class Udk0410DimmerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create one entry per bus."""
        errors = {}

        if user_input is not None:
            unique = f"{user_input[CONF_PORT]}::{int(user_input[CONF_BAUDRATE])}"
            await self.async_set_unique_id(unique)
            self._abort_if_unique_id_configured()

            title = f"UDK Bus ({user_input[CONF_PORT]})"
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_PORT, default=DEFAULT_PORT): str,
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return Udk0410DimmerOptionsFlowHandler(config_entry)


class Udk0410DimmerOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow: manage module list + per-module channel names."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_module", "remove_module"],
        )

    async def async_step_add_module(self, user_input=None):
        errors = {}
        if user_input is not None:
            modules = list(self.config_entry.options.get(CONF_MODULES, []))

            addr = int(user_input[CONF_ADDRESS])

            # Prevent duplicates
            for m in modules:
                if int(m.get(CONF_ADDRESS)) == addr:
                    errors["base"] = "address_exists"
                    break

            if not errors:
                modules.append(
                    {
                        CONF_MODULE_NAME: user_input[CONF_MODULE_NAME],
                        CONF_ADDRESS: addr,
                        CONF_CH1_NAME: user_input.get(CONF_CH1_NAME, "Dimmer 1"),
                        CONF_CH2_NAME: user_input.get(CONF_CH2_NAME, "Dimmer 2"),
                        CONF_CH3_NAME: user_input.get(CONF_CH3_NAME, "Dimmer 3"),
                        CONF_CH4_NAME: user_input.get(CONF_CH4_NAME, "Dimmer 4"),
                    }
                )

                return self.async_create_entry(title="", data={CONF_MODULES: modules})

        schema = vol.Schema(
            {
                vol.Required(CONF_MODULE_NAME, default="M01"): str,
                vol.Required(CONF_ADDRESS, default=1): vol.Coerce(int),
                vol.Optional(CONF_CH1_NAME, default="Dimmer 1"): str,
                vol.Optional(CONF_CH2_NAME, default="Dimmer 2"): str,
                vol.Optional(CONF_CH3_NAME, default="Dimmer 3"): str,
                vol.Optional(CONF_CH4_NAME, default="Dimmer 4"): str,
            }
        )
        return self.async_show_form(step_id="add_module", data_schema=schema, errors=errors)

    async def async_step_remove_module(self, user_input=None):
        modules = list(self.config_entry.options.get(CONF_MODULES, []))

        if not modules:
            return self.async_abort(reason="no_modules")

        choices = {
            str(m[CONF_ADDRESS]): f"{m.get(CONF_MODULE_NAME, 'M')} (addr {m[CONF_ADDRESS]})"
            for m in modules
        }

        if user_input is not None:
            addr = int(user_input["address_to_remove"])
            modules = [m for m in modules if int(m.get(CONF_ADDRESS)) != addr]
            return self.async_create_entry(title="", data={CONF_MODULES: modules})

        schema = vol.Schema({vol.Required("address_to_remove"): vol.In(choices)})
        return self.async_show_form(step_id="remove_module", data_schema=schema)
