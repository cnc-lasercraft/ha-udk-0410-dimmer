from __future__ import annotations
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_MODULES, MOD_NAME, MOD_ADDRESS, MOD_DIMMERS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([DimmerConfigSensor(entry)])


class DimmerConfigSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Dimmer config"
    _attr_icon = "mdi:tune-vertical"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_dimmer_config"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "UDK-04-10 Dimmer",
            "manufacturer": "UDK",
            "model": "UDK-04-10",
        }
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        self._unsub = self.entry.add_update_listener(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        pass

    async def _on_update(self, hass, entry) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        modules = self.entry.options.get(CONF_MODULES, [])
        return len(modules)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        modules = self.entry.options.get(CONF_MODULES, [])
        return {
            "modules": modules,
            "entry_id": self.entry.entry_id,
        }
