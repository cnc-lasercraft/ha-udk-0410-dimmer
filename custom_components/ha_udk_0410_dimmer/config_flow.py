from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_BAUDRATE,
    CONF_MODULES,
    MOD_NAME,
    MOD_ADDRESS,
    MOD_DIMMERS,
)

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUDRATE = 38400


def _default_modules():
    return []


class Rs485DimmerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            port = user_input[CONF_PORT]
            baudrate = int(user_input[CONF_BAUDRATE])

            # One entry per port is usually sensible; keep it simple
            await self.async_set_unique_id(f"{DOMAIN}:{port}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"HA UDK-0410 Dimmer ({port})",
                data={CONF_PORT: port, CONF_BAUDRATE: baudrate},
                options={CONF_MODULES: _default_modules()},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_PORT, default=DEFAULT_PORT): selector.TextSelector(),
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1200, max=921600, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return Rs485DimmerOptionsFlowHandler(config_entry)


class Rs485DimmerOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._config_entry = config_entry
        self._modules = list(config_entry.options.get(CONF_MODULES, []))

    async def async_step_init(self, user_input=None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_module", "edit_module", "remove_module"],
        )

    # -------- Add Module --------
    async def async_step_add_module(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            address = int(user_input[MOD_ADDRESS])
            name = user_input[MOD_NAME].strip() or f"M{address:02d}"

            if any(int(m.get(MOD_ADDRESS)) == address for m in self._modules):
                errors[MOD_ADDRESS] = "address_exists"
            else:
                # Default: 4 channels with index 1..4
                dimmers = [
                    {"index": 1, "name": user_input["d1"].strip() or f"Dimmer {address}-1"},
                    {"index": 2, "name": user_input["d2"].strip() or f"Dimmer {address}-2"},
                    {"index": 3, "name": user_input["d3"].strip() or f"Dimmer {address}-3"},
                    {"index": 4, "name": user_input["d4"].strip() or f"Dimmer {address}-4"},
                ]
                self._modules.append({MOD_NAME: name, MOD_ADDRESS: address, MOD_DIMMERS: dimmers})
                return await self._save_and_exit()

        schema = vol.Schema(
            {
                vol.Required(MOD_ADDRESS, default=1): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=247, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(MOD_NAME, default="M01"): selector.TextSelector(),
                vol.Required("d1", default="Kanal 1"): selector.TextSelector(),
                vol.Required("d2", default="Kanal 2"): selector.TextSelector(),
                vol.Required("d3", default="Kanal 3"): selector.TextSelector(),
                vol.Required("d4", default="Kanal 4"): selector.TextSelector(),
            }
        )

        return self.async_show_form(step_id="add_module", data_schema=schema, errors=errors)

    # -------- Edit Module --------
    async def async_step_edit_module(self, user_input=None) -> FlowResult:
        if not self._modules:
            return await self._save_and_exit()

        # First step: select module
        if user_input is None:
            options = {
                str(m[MOD_ADDRESS]): f"{m.get(MOD_NAME, '')} (addr {m[MOD_ADDRESS]})"
                for m in self._modules
            }
            schema = vol.Schema({vol.Required("module"): vol.In(options)})
            return self.async_show_form(step_id="edit_module", data_schema=schema)

        addr = int(user_input["module"])
        module = next((m for m in self._modules if int(m.get(MOD_ADDRESS)) == addr), None)
        if module is None:
            return await self._save_and_exit()

        self._editing_addr = addr
        return await self.async_step_edit_module_details()

    async def async_step_edit_module_details(self, user_input=None) -> FlowResult:
        module = next((m for m in self._modules if int(m.get(MOD_ADDRESS)) == int(self._editing_addr)), None)
        if module is None:
            return await self._save_and_exit()

        if user_input is not None:
            module[MOD_NAME] = user_input[MOD_NAME].strip() or module.get(MOD_NAME, f"M{module[MOD_ADDRESS]:02d}")
            dimmers = module.get(MOD_DIMMERS, [])
            # Ensure list length 4
            while len(dimmers) < 4:
                dimmers.append({"index": len(dimmers) + 1, "name": f"Kanal {len(dimmers) + 1}"})
            for i in range(4):
                key = f"d{i+1}"
                dimmers[i]["index"] = i + 1
                dimmers[i]["name"] = user_input.get(key, dimmers[i].get("name", f"Kanal {i+1}")).strip() or f"Kanal {i+1}"
            module[MOD_DIMMERS] = dimmers[:4]
            return await self._save_and_exit()

        dimmers = module.get(MOD_DIMMERS, [])
        while len(dimmers) < 4:
            dimmers.append({"index": len(dimmers) + 1, "name": f"Kanal {len(dimmers) + 1}"})

        schema = vol.Schema(
            {
                vol.Required(MOD_NAME, default=module.get(MOD_NAME, f"M{module[MOD_ADDRESS]:02d}")): selector.TextSelector(),
                vol.Required("d1", default=dimmers[0].get("name", "Kanal 1")): selector.TextSelector(),
                vol.Required("d2", default=dimmers[1].get("name", "Kanal 2")): selector.TextSelector(),
                vol.Required("d3", default=dimmers[2].get("name", "Kanal 3")): selector.TextSelector(),
                vol.Required("d4", default=dimmers[3].get("name", "Kanal 4")): selector.TextSelector(),
            }
        )

        return self.async_show_form(step_id="edit_module_details", data_schema=schema)

    # -------- Remove Module --------
    async def async_step_remove_module(self, user_input=None) -> FlowResult:
        if not self._modules:
            return await self._save_and_exit()

        if user_input is not None:
            addr = int(user_input["module"])
            self._modules = [m for m in self._modules if int(m.get(MOD_ADDRESS)) != addr]
            return await self._save_and_exit()

        options = {
            str(m[MOD_ADDRESS]): f"{m.get(MOD_NAME, '')} (addr {m[MOD_ADDRESS]})"
            for m in self._modules
        }
        schema = vol.Schema({vol.Required("module"): vol.In(options)})
        return self.async_show_form(step_id="remove_module", data_schema=schema)

    async def _save_and_exit(self) -> FlowResult:
        return self.async_create_entry(title="", data={CONF_MODULES: self._modules})
