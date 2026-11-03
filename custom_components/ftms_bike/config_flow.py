"""Config flow: pick the bike from what Home Assistant's Bluetooth can hear.

Setting up never connects to the bike, so it can't get in the way of an app that's
using it at the time.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers import selector

from . import ftms
from .const import CONF_RESISTANCE_SCALE, DOMAIN

AUTO = "auto"


def _is_bike(info: bluetooth.BluetoothServiceInfoBleak) -> bool:
    return (ftms.FTMS_SERVICE in info.service_uuids
            and ftms.is_indoor_bike(info.service_data.get(ftms.FTMS_SERVICE)))


class FtmsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered: bluetooth.BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if not _is_bike(discovery_info):
            return self.async_abort(reason="not_a_bike")
        self._discovered = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name or discovery_info.address}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        info = self._discovered
        assert info is not None
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME],
                                           data={CONF_ADDRESS: info.address})
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default="Indoor bike"): str}),
            description_placeholders={"name": info.name or info.address},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME],
                                           data={CONF_ADDRESS: address})

        current = self._async_current_ids()
        options = [
            selector.SelectOptionDict(
                value=info.address,
                label=(f"{info.name} ({info.address}, {info.rssi} dBm)"
                       if info.name and info.name != info.address
                       else f"{info.address} ({info.rssi} dBm)"))
            for info in bluetooth.async_discovered_service_info(self.hass, connectable=True)
            if info.address not in current and _is_bike(info)
        ]
        if not options:
            return self.async_abort(reason="no_bikes")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): selector.SelectSelector(selector.SelectSelectorConfig(
                    options=options, mode=selector.SelectSelectorMode.DROPDOWN)),
                vol.Required(CONF_NAME, default="Indoor bike"): str,
            }),
        )

    @staticmethod
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return FtmsOptionsFlow()


class FtmsOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            scale = user_input[CONF_RESISTANCE_SCALE]
            return self.async_create_entry(
                data={} if scale == AUTO else {CONF_RESISTANCE_SCALE: scale})
        current = self.config_entry.options.get(CONF_RESISTANCE_SCALE, AUTO)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_RESISTANCE_SCALE, default=current): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[AUTO, ftms.SCALE_TENTHS, ftms.SCALE_SPREAD],
                        translation_key=CONF_RESISTANCE_SCALE)),
            }),
        )
