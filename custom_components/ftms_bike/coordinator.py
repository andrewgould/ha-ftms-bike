"""Talks to the bike only during a session that someone started.

Consoles take one Bluetooth connection at a time, so holding one permanently would
lock out training apps like Kinomap and Zwift. Instead nothing connects until the
session switch is turned on, and the session ends when it's turned off, when the
bike drops the connection, or after IDLE_TIMEOUT without pedalling. Nothing
reconnects by itself, and a session never survives a restart.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import ftms
from .const import (
    COMMAND_TIMEOUT,
    CONF_RESISTANCE_SCALE,
    DEFAULT_RESISTANCE_RANGE,
    DOMAIN,
    IDLE_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

ERRORS = (BleakError, TimeoutError, EOFError)


@dataclass
class BikeState:
    in_range: bool = False
    connected: bool = False
    # Latest value of each Indoor Bike Data field, keyed as ftms.parse_indoor_bike_data names them.
    values: dict[str, float | int] = field(default_factory=dict)
    resistance_range: tuple[int, int, int] | None = None
    power_range: tuple[int, int, int] | None = None
    # What was last asked of the bike this session.
    target_resistance: float | None = None
    target_power: int | None = None


type FtmsConfigEntry = ConfigEntry[FtmsCoordinator]


class FtmsCoordinator(DataUpdateCoordinator[BikeState]):
    """Push-style: notifications call async_set_updated_data."""

    def __init__(self, hass: HomeAssistant, entry: FtmsConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=entry.title, config_entry=entry)
        self.address: str = entry.data[CONF_ADDRESS]
        self.data = BikeState()
        self._client: BleakClientWithServiceCache | None = None
        self._has_control = False
        self._command_lock = asyncio.Lock()
        self._response: asyncio.Future[tuple[int, int]] | None = None
        self._last_pedal = 0.0
        self._cancel_idle = None
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.address)},
            connections={(CONNECTION_BLUETOOTH, self.address)},
            name=entry.title,
            manufacturer="Bluetooth fitness machine",
            model="Indoor bike",
        )

    async def async_start(self) -> None:
        self.data.in_range = bluetooth.async_address_present(self.hass, self.address, True)
        # The entities already exist; tell them. Unchanged advertisements don't
        # call _on_advertisement, so it can't be relied on to do this.
        self.async_set_updated_data(self.data)
        entry = self.config_entry
        entry.async_on_unload(bluetooth.async_register_callback(
            self.hass, self._on_advertisement,
            bluetooth.BluetoothCallbackMatcher(address=self.address, connectable=True),
            bluetooth.BluetoothScanningMode.ACTIVE,
        ))
        entry.async_on_unload(bluetooth.async_track_unavailable(
            self.hass, self._on_unavailable, self.address, connectable=True))

    async def async_stop(self) -> None:
        await self.async_end_session("unloading")

    @callback
    def _on_advertisement(self, info: bluetooth.BluetoothServiceInfoBleak,
                          change: bluetooth.BluetoothChange) -> None:
        if not self.data.in_range:
            self.data.in_range = True
            self.async_set_updated_data(self.data)

    @callback
    def _on_unavailable(self, info: bluetooth.BluetoothServiceInfoBleak) -> None:
        # Some consoles stop advertising while connected, so silence only counts
        # when there's no session.
        if not self.data.connected and self.data.in_range:
            self.data.in_range = False
            self.async_set_updated_data(self.data)

    # Sessions

    async def async_start_session(self) -> None:
        if self._client is not None:
            return
        device = bluetooth.async_ble_device_from_address(self.hass, self.address, True)
        if device is None:
            raise HomeAssistantError(
                "The bike isn't advertising. Pedal for a moment to wake its console.")
        try:
            client = await establish_connection(
                BleakClientWithServiceCache, device, self.config_entry.title,
                disconnected_callback=self._on_disconnect, max_attempts=2)
        except ERRORS as err:
            _LOGGER.debug("%s: connect failed: %s", self.address, err)
            raise HomeAssistantError(
                "Couldn't connect to the bike. Is Kinomap or another app connected to it?"
            ) from err
        self._client = client
        try:
            await self._set_up(client)
        except ERRORS as err:
            await self.async_end_session(f"setup failed: {err}")
            raise HomeAssistantError(f"The bike connected but didn't set up: {err}") from err
        self._last_pedal = time.monotonic()
        self._cancel_idle = async_track_time_interval(
            self.hass, self._check_idle, timedelta(seconds=30))
        _LOGGER.info("%s: session started", self.address)

    async def _set_up(self, client: BleakClientWithServiceCache) -> None:
        state = self.data
        if client.services.get_characteristic(ftms.INDOOR_BIKE_DATA) is None:
            raise BleakError("no Indoor Bike Data characteristic; is this an indoor bike?")
        for uuid, attr in ((ftms.RESISTANCE_RANGE, "resistance_range"),
                           (ftms.POWER_RANGE, "power_range")):
            if client.services.get_characteristic(uuid) is not None:
                setattr(state, attr, ftms.parse_range(await client.read_gatt_char(uuid)))
        if client.services.get_characteristic(ftms.CONTROL_POINT) is not None:
            await client.start_notify(ftms.CONTROL_POINT, self._on_control_point)
        await client.start_notify(ftms.INDOOR_BIKE_DATA, self._on_bike_data)
        state.connected = state.in_range = True
        state.values = {}
        state.target_resistance = state.target_power = None
        self.async_set_updated_data(state)

    async def async_end_session(self, reason: str = "turned off") -> None:
        client, self._client = self._client, None
        self._has_control = False
        if self._cancel_idle:
            self._cancel_idle()
            self._cancel_idle = None
        if client is not None:
            _LOGGER.info("%s: session ended (%s)", self.address, reason)
            try:
                await client.disconnect()
            except ERRORS:
                pass
        state = self.data
        if state.connected:
            state.connected = False
            state.values = {}
            state.in_range = bluetooth.async_address_present(self.hass, self.address, True)
            self.async_set_updated_data(state)

    @callback
    def _on_disconnect(self, client: BleakClientWithServiceCache) -> None:
        if client is self._client:
            self.hass.async_create_task(self.async_end_session("the bike disconnected"))

    @callback
    def _check_idle(self, _now) -> None:
        if time.monotonic() - self._last_pedal > IDLE_TIMEOUT:
            self.hass.async_create_task(
                self.async_end_session(f"no pedalling for {IDLE_TIMEOUT // 60} minutes"))

    # Notifications

    def _on_bike_data(self, _char, data: bytearray) -> None:
        try:
            fields = ftms.parse_indoor_bike_data(bytes(data))
        except Exception:  # a malformed frame shouldn't end the session
            _LOGGER.debug("%s: couldn't parse %s", self.address, data.hex())
            return
        if fields.get("cadence", 0) > 0:
            self._last_pedal = time.monotonic()
        state = self.data
        # Consoles send each reading more than once; only push changes.
        if any(state.values.get(k) != v for k, v in fields.items()):
            state.values.update(fields)
            self.async_set_updated_data(state)

    def _on_control_point(self, _char, data: bytearray) -> None:
        response = ftms.parse_response(bytes(data))
        if response and self._response and not self._response.done():
            self._response.set_result(response)

    # Commands

    async def _command(self, payload: bytes) -> None:
        if self._client is None:
            raise HomeAssistantError("Start a bike session first.")
        async with self._command_lock:
            try:
                if not self._has_control:
                    await self._send(ftms.request_control())
                    self._has_control = True
                try:
                    await self._send(payload)
                except ftms.FtmsError as err:
                    if err.args[0] != ftms.RESULT_NOT_PERMITTED:
                        raise
                    # The console forgot we had control (some do after a pause); ask again.
                    await self._send(ftms.request_control())
                    await self._send(payload)
            except ftms.FtmsError as err:
                raise HomeAssistantError(err.args[1]) from err

    async def _send(self, payload: bytes) -> None:
        client = self._client
        if client is None:
            raise HomeAssistantError("The bike session ended.")
        self._response = self.hass.loop.create_future()
        try:
            await client.write_gatt_char(ftms.CONTROL_POINT, payload, response=True)
            async with asyncio.timeout(COMMAND_TIMEOUT):
                op, result = await self._response
        except ERRORS as err:
            raise HomeAssistantError(f"The bike didn't answer: {err}") from err
        finally:
            self._response = None
        if op != payload[0] or result != ftms.RESULT_SUCCESS:
            raise ftms.FtmsError(result, f"The bike said {ftms.RESULTS.get(result, hex(result))}.")

    async def async_set_resistance(self, level: float) -> None:
        supported = self.data.resistance_range or DEFAULT_RESISTANCE_RANGE
        scale = (self.config_entry.options.get(CONF_RESISTANCE_SCALE)
                 or ftms.default_scale(supported))
        await self._command(ftms.set_resistance(ftms.resistance_raw(level, supported, scale)))
        self.data.target_resistance = level
        self.data.target_power = None
        self.async_set_updated_data(self.data)

    async def async_set_power(self, watts: int) -> None:
        await self._command(ftms.set_power(watts))
        self.data.target_power = watts
        self.async_set_updated_data(self.data)
