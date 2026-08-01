from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE, CONF_MODULES

_LOGGER = logging.getLogger("custom_components.ha_udk_0410_dimmer")

PLATFORMS: list[str] = ["light", "sensor"]


@dataclass
class Rs485Runtime:
    port: str
    baudrate: int


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration (YAML not used)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    port = entry.data.get(CONF_PORT)
    baudrate = entry.data.get(CONF_BAUDRATE)

    if not port or not baudrate:
        _LOGGER.error("Missing port/baudrate in config entry")
        return False

    hass.data[DOMAIN][entry.entry_id] = Rs485Runtime(port=port, baudrate=int(baudrate))

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as err:
        _LOGGER.exception("Failed to forward setup: %s", err)
        raise ConfigEntryNotReady from err

    # --- Services for dashboard card ---
    async def _update_module_service(call: ServiceCall) -> None:
        address = int(call.data.get("address", 0))
        key = str(call.data.get("key", ""))
        value = call.data.get("value")
        if address < 1 or not key:
            return
        modules = copy.deepcopy(list(entry.options.get(CONF_MODULES, [])))
        for m in modules:
            if int(m.get("address", 0)) == address:
                if key.startswith("d") and key[1:].isdigit():
                    idx = int(key[1:]) - 1
                    dimmers = m.get("dimmers", [])
                    while len(dimmers) <= idx:
                        dimmers.append({"index": len(dimmers) + 1, "name": ""})
                    dimmers[idx]["name"] = str(value or "")
                    m["dimmers"] = dimmers
                elif key == "name":
                    m["name"] = str(value or "")
                break
        new_options = dict(entry.options)
        new_options[CONF_MODULES] = modules
        hass.config_entries.async_update_entry(entry, options=new_options)

    async def _add_module_service(call: ServiceCall) -> None:
        address = int(call.data.get("address", 0))
        name = str(call.data.get("name", "")).strip()
        if address < 1:
            return
        modules = copy.deepcopy(list(entry.options.get(CONF_MODULES, [])))
        if any(int(m.get("address", 0)) == address for m in modules):
            return
        if not name:
            name = f"M{address:02d}"
        dimmers = [{"index": i+1, "name": f"Dimmer {i+1}"} for i in range(4)]
        modules.append({"name": name, "address": address, "dimmers": dimmers})
        modules.sort(key=lambda m: int(m.get("address", 0)))
        new_options = dict(entry.options)
        new_options[CONF_MODULES] = modules
        hass.config_entries.async_update_entry(entry, options=new_options)
        # Reload to create new light entities
        hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))

    async def _remove_module_service(call: ServiceCall) -> None:
        address = int(call.data.get("address", 0))
        if address < 1:
            return
        modules = copy.deepcopy(list(entry.options.get(CONF_MODULES, [])))
        modules = [m for m in modules if int(m.get("address", 0)) != address]
        new_options = dict(entry.options)
        new_options[CONF_MODULES] = modules
        hass.config_entries.async_update_entry(entry, options=new_options)
        # Reload to remove light entities
        hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))

    for svc_name, svc_fn in [
        ("update_module", _update_module_service),
        ("add_module", _add_module_service),
        ("remove_module", _remove_module_service),
    ]:
        hass.services.async_register(DOMAIN, svc_name, svc_fn)

    return True

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # Only log, don't auto-reload — services handle reload when needed
    _LOGGER.debug("HA UDK-0410 Dimmer: Optionen geändert")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime = hass.data[DOMAIN].pop(entry.entry_id, None)
        # Die gecachte serielle Verbindung schliessen, damit ein Reload wirklich
        # neu verbindet — sonst redet er weiter mit einem toten File-Descriptor
        # (z.B. nach USB-Reset oder Re-Enumeration des Adapters).
        if runtime is not None:
            port_map = hass.data.get(DOMAIN + "_ports", {})
            module_obj = port_map.pop(f"{runtime.port}@{runtime.baudrate}", None)
            if module_obj is not None:
                await module_obj.close()
        for svc_name in ("update_module", "add_module", "remove_module"):
            hass.services.async_remove(DOMAIN, svc_name)
    return unload_ok
