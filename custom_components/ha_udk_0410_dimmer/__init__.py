from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE

_LOGGER = logging.getLogger("custom_components.ha_udk_0410_dimmer")

PLATFORMS: list[str] = ["light"]


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

    return True

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the entry."""
    _LOGGER.info("HA UDK-0410 Dimmer: Optionen geändert, lade Integration neu")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
