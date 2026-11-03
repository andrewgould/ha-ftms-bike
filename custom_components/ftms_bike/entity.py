"""Base entity for the bike."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import FtmsCoordinator


class FtmsEntity(CoordinatorEntity[FtmsCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FtmsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = coordinator.device_info
