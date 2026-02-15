"""Platform support for RS485 dimmer.

Robust ACK handling:
- flushes stale bytes before sending (best-effort)
- reads in small chunks until an ACK pattern is found or a deadline is hit
- structured debug logs (sent hex, received hex, buffer lengths, timeouts, retries)

ACK frame expected (4 bytes): FE <module_address> 06 FF
"""

from __future__ import annotations

import asyncio
import binascii
import logging
import time
from typing import Optional, Tuple

import serial_asyncio
from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_MODULES, DOMAIN, MOD_ADDRESS, MOD_DIMMERS, MOD_NAME

_LOGGER = logging.getLogger("custom_components.ha_udk_0410_dimmer")


class Rs485Module:
    """Shared RS485 connection per serial port (with a lock)."""

    def __init__(
        self,
        port: str = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG00Y9JZ-if00-port0",
        baudrate: int = 38400,
    ):
        self.port = port
        self.baudrate = baudrate
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._writer is not None and self._reader is not None:
            return

        _LOGGER.debug("RS485: Öffne serielle Verbindung %s @ %d", self.port, self.baudrate)
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self.port, baudrate=self.baudrate, bytesize=8, parity="N", stopbits=1
        )
        _LOGGER.debug("RS485: Serielle Verbindung zu %s aufgebaut", self.port)
        _LOGGER.info("HA UDK-0410 Dimmer: Verbunden mit %s @ %d baud", self.port, self.baudrate)

    async def _flush_input(self, flush_window_s: float = 0.08) -> bytes:
        """Best-effort flush of stale bytes."""
        if self._reader is None:
            return b""

        flushed = bytearray()
        deadline = time.monotonic() + flush_window_s

        while time.monotonic() < deadline:
            try:
                chunk = await asyncio.wait_for(self._reader.read(1024), timeout=0.01)
            except asyncio.TimeoutError:
                break
            if not chunk:
                break
            flushed.extend(chunk)

        if flushed:
            _LOGGER.debug(
                "RS485: Flushed %d bytes stale input: %s",
                len(flushed),
                binascii.hexlify(flushed).decode(),
            )
        return bytes(flushed)

    async def send_and_wait_for(
        self,
        message: bytes,
        patterns: list[bytes],
        *,
        timeout_total: float = 0.8,
        read_chunk_timeout: float = 0.12,
        max_buffer: int = 4096,
        flush_before_send: bool = True,
    ) -> Tuple[bytes, Optional[bytes]]:
        """Send a message and read until one of the patterns appears or timeout."""
        if self._writer is None or self._reader is None:
            _LOGGER.warning("RS485: Verbindung nicht hergestellt (port %s)", self.port)
            return b"", None

        async with self._lock:
            if flush_before_send:
                await self._flush_input()

            _LOGGER.debug("RS485: Sende (hex): %s", binascii.hexlify(message).decode())
            try:
                self._writer.write(message)
                await self._writer.drain()
            except Exception as err:
                _LOGGER.warning("RS485: Fehler beim Schreiben auf %s: %s", self.port, err)
                return b"", None

            buf = bytearray()
            deadline = time.monotonic() + timeout_total

            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                chunk_timeout = min(read_chunk_timeout, max(0.01, remaining))

                try:
                    chunk = await asyncio.wait_for(self._reader.read(1024), timeout=chunk_timeout)
                except asyncio.TimeoutError:
                    continue
                except Exception as err:
                    _LOGGER.warning("RS485: Fehler beim Lesen auf %s: %s", self.port, err)
                    break

                if chunk:
                    buf.extend(chunk)

                    if len(buf) > max_buffer:
                        buf[:] = buf[-max_buffer:]

                    for p in patterns:
                        if p in buf:
                            _LOGGER.debug(
                                "RS485: Match gefunden (%s) im Buffer (%d bytes): %s",
                                binascii.hexlify(p).decode(),
                                len(buf),
                                binascii.hexlify(buf).decode(),
                            )
                            return bytes(buf), p

                    _LOGGER.debug(
                        "RS485: Chunk %d bytes, Buffer %d bytes: %s",
                        len(chunk),
                        len(buf),
                        binascii.hexlify(chunk).decode(),
                    )

            if buf:
                _LOGGER.debug(
                    "RS485: Timeout ohne Match. Buffer (%d bytes): %s",
                    len(buf),
                    binascii.hexlify(buf).decode(),
                )
            else:
                _LOGGER.debug("RS485: Timeout ohne Match. Buffer leer.")
            return bytes(buf), None


class Rs485Dimmer(LightEntity):
    SYNC_BYTE = 0xFF
    START_BYTE = 0xFE
    STOP_BYTE = 0xFF
    CMD_SET = 0x57

    def __init__(self, hass, name: str, module: Rs485Module, module_address: int, dimmer_index: int):
        self.hass = hass
        self._name = name
        self.module = module
        self.module_address = int(module_address)
        self.dimmer_index = int(dimmer_index)
        self._is_on = False
        self._brightness = 0
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._unique_id: str | None = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @unique_id.setter
    def unique_id(self, value):
        self._unique_id = value

    @property
    def is_on(self):
        return self._is_on

    @property
    def brightness(self):
        return self._brightness

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS

    def _build_data_array(self, level: int, dimm_time_s: int) -> list[int]:
        levels = [1, 1, 1, 1]
        times = [5, 5, 5, 5]
        idx = max(0, min(3, self.dimmer_index - 1))
        levels[idx] = max(0, min(255, int(level)))
        times[idx] = max(0, min(255, int(dimm_time_s)))
        data: list[int] = []
        for i in range(4):
            data.append(levels[i])
            data.append(times[i])
        return data

    def _ack_pattern(self) -> bytes:
        return bytes([0xFE, self.module_address, 0x06, 0xFF])

    async def sende_befehl_mit_ack(
        self,
        message: bytes,
        *,
        max_wiederholungen: int = 3,
        timeout_total: float = 0.8,
        read_chunk_timeout: float = 0.12,
    ) -> bool:
        ack_pat = self._ack_pattern()

        for attempt in range(1, max_wiederholungen + 1):
            _LOGGER.debug(
                "RS485Dimmer[%s]: Sende Versuch %d/%d (addr=%d idx=%d)",
                self._name,
                attempt,
                max_wiederholungen,
                self.module_address,
                self.dimmer_index,
            )

            buf, matched = await self.module.send_and_wait_for(
                message,
                patterns=[ack_pat],
                timeout_total=timeout_total,
                read_chunk_timeout=read_chunk_timeout,
                flush_before_send=True,
            )

            if matched == ack_pat:
                _LOGGER.debug(
                    "RS485Dimmer[%s]: ACK OK (addr=%d). BufferLen=%d",
                    self._name,
                    self.module_address,
                    len(buf),
                )
                return True

            _LOGGER.warning(
                "RS485Dimmer[%s]: Kein ACK (attempt %d/%d). BufferLen=%d Buffer=%s",
                self._name,
                attempt,
                max_wiederholungen,
                len(buf),
                binascii.hexlify(buf).decode() if buf else "",
            )

        return False

    async def async_turn_on(self, **kwargs):
        level = kwargs.get(ATTR_BRIGHTNESS, 255)
        transition = kwargs.get("transition")

        if transition is not None:
            try:
                dimm_time_s = int(float(transition))
            except Exception:
                dimm_time_s = 5
        else:
            dimm_time_s = 5

        data = self._build_data_array(level, dimm_time_s)
        payload = [self.module_address, self.CMD_SET] + data
        checksum = (sum(payload) & 0xFF) & 0x7F

        message = bytes(
            [self.SYNC_BYTE, self.START_BYTE, self.module_address, self.CMD_SET]
            + data
            + [checksum, self.STOP_BYTE]
        )

        _LOGGER.debug("RS485Dimmer[%s]: Sende Set -> %s", self._name, binascii.hexlify(message).decode())

        success = await self.sende_befehl_mit_ack(
            message,
            max_wiederholungen=3,
            timeout_total=0.8,
            read_chunk_timeout=0.12,
        )

        if success:
            self._is_on = True
            self._brightness = level
        else:
            _LOGGER.warning("RS485Dimmer[%s]: Einschalten nicht bestätigt (kein ACK).", self._name)

        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        transition = kwargs.get("transition")

        if transition is not None:
            try:
                dimm_time_s = int(float(transition))
            except Exception:
                dimm_time_s = 5
        else:
            dimm_time_s = 5

        data = self._build_data_array(0, dimm_time_s)
        payload = [self.module_address, self.CMD_SET] + data
        checksum = (sum(payload) & 0xFF) & 0x7F

        message = bytes(
            [self.SYNC_BYTE, self.START_BYTE, self.module_address, self.CMD_SET]
            + data
            + [checksum, self.STOP_BYTE]
        )

        _LOGGER.debug("RS485Dimmer[%s]: Sende Off -> %s", self._name, binascii.hexlify(message).decode())

        success = await self.sende_befehl_mit_ack(
            message,
            max_wiederholungen=3,
            timeout_total=0.8,
            read_chunk_timeout=0.12,
        )

        if not success:
            _LOGGER.warning("RS485Dimmer[%s]: Ausschalten nicht bestätigt (kein ACK).", self._name)
            return

        self._is_on = False
        self._brightness = 0
        self.async_schedule_update_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up dimmer entities from a config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]

    # Read options first (UI config), fallback to data (initial setup)
    modules_cfg = entry.options.get(CONF_MODULES, []) or entry.data.get(CONF_MODULES, [])

    _LOGGER.debug(
        "ha_udk_0410_dimmer: async_setup_entry port=%s baud=%s modules=%d",
        runtime.port,
        runtime.baudrate,
        len(modules_cfg),
    )

    entities: list[Rs485Dimmer] = []

    port_map = hass.data.setdefault(DOMAIN + "_ports", {})
    port_key = f"{runtime.port}@{runtime.baudrate}"
    module_obj = port_map.get(port_key)
    if module_obj is None:
        module_obj = Rs485Module(port=runtime.port, baudrate=int(runtime.baudrate))
        await module_obj.connect()
        port_map[port_key] = module_obj

    ent_reg = er.async_get(hass)

    for module_cfg in modules_cfg:
        module_name = module_cfg.get(MOD_NAME, "Module")
        module_addr = int(module_cfg.get(MOD_ADDRESS, 1))

        dimmers = list(module_cfg.get(MOD_DIMMERS, []) or [])
        while len(dimmers) < 4:
            dimmers.append({"index": len(dimmers) + 1, "name": f"Kanal {len(dimmers) + 1}"})

        for idx, d in enumerate(dimmers[:4]):
            dimmer_name = d.get("name", f"Dimmer {idx+1}")
            dimmer_index = int(d.get("index", idx + 1))
            full_name = f"{module_name}D{dimmer_index} - {dimmer_name}"

            entity = Rs485Dimmer(
                hass,
                full_name,
                module_obj,
                module_address=module_addr,
                dimmer_index=dimmer_index,
            )
            unique_id = f"ha_udk_0410_dimmer_{module_addr}_{dimmer_index}"
            entity.unique_id = unique_id

            existing_entity_id = ent_reg.async_get_entity_id("light", DOMAIN, unique_id)
            if existing_entity_id:
                entry_obj = ent_reg.async_get(existing_entity_id)
                current_name = (entry_obj.name or "") if entry_obj else ""
                if current_name != full_name:
                    _LOGGER.info(
                        "HA UDK-0410 Dimmer: Aktualisiere Namen %s -> %s",
                        existing_entity_id,
                        full_name,
                    )
                    ent_reg.async_update_entity(existing_entity_id, name=full_name)

            entities.append(entity)

    if entities:
        async_add_entities(entities, True)

    _LOGGER.info("HA UDK-0410 Dimmer: %d Light-Entities erstellt", len(entities))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entry."""
    return True
