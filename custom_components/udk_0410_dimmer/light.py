"""Light platform for UDK-04-10 (RS-485/DMX) dimmer modules.

UI model (Option B):
  - ONE config entry represents the RS-485 bus (port + baudrate).
  - Modules are stored in config entry OPTIONS as a list.
  - Each module creates 4 light entities.

Legacy YAML is also supported.
"""

from __future__ import annotations

import asyncio
import binascii
import logging
from dataclasses import dataclass
from typing import Optional

import serial_asyncio
from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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

_LOGGER = logging.getLogger(__name__)


class Rs485Bus:
    """One shared serial bus per port+baudrate."""

    def __init__(self, port: str, baudrate: int) -> None:
        self.port = port
        self.baudrate = baudrate
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._writer is not None and self._reader is not None:
            return
        _LOGGER.debug("Öffne serielle Verbindung %s @ %d", self.port, self.baudrate)
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self.port, baudrate=self.baudrate, bytesize=8, parity="N", stopbits=1
        )
        _LOGGER.debug("Serielle Verbindung zu %s aufgebaut", self.port)

    async def send(self, message: bytes, timeout: float = 1.0) -> Optional[bytes]:
        if self._writer is None or self._reader is None:
            _LOGGER.warning("RS485: Verbindung nicht hergestellt (port %s)", self.port)
            return None

        async with self._lock:
            try:
                _LOGGER.debug("Sende (hex): %s", binascii.hexlify(message).decode())
                self._writer.write(message)
                await self._writer.drain()
                try:
                    response = await asyncio.wait_for(self._reader.read(1024), timeout=timeout)
                    _LOGGER.debug("Empfang (raw): %s", response)
                    return response
                except asyncio.TimeoutError:
                    _LOGGER.warning("Keine Antwort innerhalb Timeout (%.2fs)", timeout)
                    return b""
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Fehler beim Senden auf %s: %s", self.port, err)
                return None


@dataclass(frozen=True)
class ModuleConfig:
    name: str
    address: int
    ch_names: dict[int, str]  # 1..4


def _get_bus(hass: HomeAssistant, port: str, baudrate: int) -> Rs485Bus:
    data = hass.data.setdefault(DOMAIN, {})
    buses = data.setdefault("buses", {})
    key = f"{port}::{baudrate}"
    if key not in buses:
        buses[key] = Rs485Bus(port=port, baudrate=baudrate)
    return buses[key]


class Udk0410DimmerChannel(LightEntity):
    """One dimmer channel (1..4) on a module."""

    SYNC_BYTE = 0xFF
    START_BYTE = 0xFE
    STOP_BYTE = 0xFF
    CMD_SET = 0x57

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, port: str, module: ModuleConfig, bus: Rs485Bus, channel: int) -> None:
        self._port = port
        self._module = module
        self._bus = bus
        self._channel = channel

        self._attr_name = f"{module.name} D{channel} - {module.ch_names[channel]}"
        self._attr_unique_id = f"{DOMAIN}_{port}_{module.address}_{channel}"

        self._attr_is_on = False
        self._attr_brightness = 0

    def _build_data_array(self, level: int, dimm_time_s: int) -> list[int]:
        levels = [1, 1, 1, 1]
        times = [5, 5, 5, 5]
        idx = max(0, min(3, self._channel - 1))
        levels[idx] = max(0, min(255, int(level)))
        times[idx] = max(0, min(255, int(dimm_time_s)))

        data: list[int] = []
        for i in range(4):
            data.append(levels[i])
            data.append(times[i])
        return data

    def _checksum_7bit(self, payload: list[int]) -> int:
        return (sum(payload) & 0xFF) & 0x7F

    def _build_set_message(self, level: int, dimm_time_s: int) -> bytes:
        data = self._build_data_array(level, dimm_time_s)
        payload = [self._module.address, self.CMD_SET] + data
        checksum = self._checksum_7bit(payload)
        return bytes(
            [self.SYNC_BYTE, self.START_BYTE, self._module.address, self.CMD_SET]
            + data
            + [checksum, self.STOP_BYTE]
        )

    def _is_ack(self, response: bytes) -> bool:
        return (
            len(response) >= 4
            and response[0] == 0xFE
            and response[1] == self._module.address
            and response[2] == 0x06
            and response[3] == 0xFF
        )

    async def _send_with_ack(self, message: bytes, retries: int = 3, timeout: float = 0.5) -> bool:
        for attempt in range(1, retries + 1):
            _LOGGER.debug("Sende Versuch %d/%d (%s)", attempt, retries, self.name)
            response = await self._bus.send(message, timeout=timeout)
            if response is None:
                continue
            if self._is_ack(response):
                return True
        return False

    async def async_turn_on(self, **kwargs) -> None:
        level = int(kwargs.get(ATTR_BRIGHTNESS, 255))
        transition = kwargs.get("transition")
        try:
            dimm_time_s = int(float(transition)) if transition is not None else 5
        except Exception:  # noqa: BLE001
            dimm_time_s = 5

        message = self._build_set_message(level, dimm_time_s)
        ok = await self._send_with_ack(message)
        if ok:
            self._attr_is_on = True
            self._attr_brightness = level
        else:
            _LOGGER.warning("Kein ACK bei %s", self.name)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        transition = kwargs.get("transition")
        try:
            dimm_time_s = int(float(transition)) if transition is not None else 5
        except Exception:  # noqa: BLE001
            dimm_time_s = 5

        message = self._build_set_message(0, dimm_time_s)
        ok = await self._send_with_ack(message)
        if ok:
            self._attr_is_on = False
            self._attr_brightness = 0
        else:
            _LOGGER.warning("Kein ACK bei %s", self.name)
        self.async_write_ha_state()


def _modules_from_options(entry: ConfigEntry) -> list[ModuleConfig]:
    modules_raw = entry.options.get(CONF_MODULES, []) or []
    modules: list[ModuleConfig] = []

    for m in modules_raw:
        name = str(m.get(CONF_MODULE_NAME, f"M{int(m.get(CONF_ADDRESS, 1)):02d}"))
        address = int(m.get(CONF_ADDRESS, 1))
        ch_names = {
            1: str(m.get(CONF_CH1_NAME, "Dimmer 1")),
            2: str(m.get(CONF_CH2_NAME, "Dimmer 2")),
            3: str(m.get(CONF_CH3_NAME, "Dimmer 3")),
            4: str(m.get(CONF_CH4_NAME, "Dimmer 4")),
        }
        modules.append(ModuleConfig(name=name, address=address, ch_names=ch_names))

    return modules


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    port = str(entry.data.get(CONF_PORT, DEFAULT_PORT))
    baudrate = int(entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE))

    bus = _get_bus(hass, port, baudrate)
    await bus.connect()

    entities: list[Udk0410DimmerChannel] = []
    for module in _modules_from_options(entry):
        for ch in (1, 2, 3, 4):
            entities.append(Udk0410DimmerChannel(port, module, bus, ch))

    if entities:
        async_add_entities(entities, True)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Legacy YAML platform."""
    _LOGGER.debug("Setting up %s platform (YAML)", DOMAIN)

    port = str(config.get(CONF_PORT, DEFAULT_PORT))
    baudrate = int(config.get(CONF_BAUDRATE, DEFAULT_BAUDRATE))
    bus = _get_bus(hass, port, baudrate)
    await bus.connect()

    modules_cfg = config.get("modules", [])
    entities: list[Udk0410DimmerChannel] = []

    for module_cfg in modules_cfg:
        module_name = str(module_cfg.get("name", "Module"))
        module_addr = int(module_cfg.get("address", 1))

        ch_names = {1: "Dimmer 1", 2: "Dimmer 2", 3: "Dimmer 3", 4: "Dimmer 4"}
        for idx, d in enumerate((module_cfg.get("dimmers", []) or [])[:4]):
            ch = int(d.get("index", idx + 1))
            ch = max(1, min(4, ch))
            ch_names[ch] = str(d.get("name", ch_names[ch]))

        module = ModuleConfig(name=module_name, address=module_addr, ch_names=ch_names)
        for ch in (1, 2, 3, 4):
            entities.append(Udk0410DimmerChannel(port, module, bus, ch))

    if entities:
        async_add_entities(entities, True)
