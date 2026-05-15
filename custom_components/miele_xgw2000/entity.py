"""Base entity for Miele XGW 2000."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MieleCoordinator


class MieleEntity(CoordinatorEntity[MieleCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: MieleCoordinator, uid: str) -> None:
        super().__init__(coordinator)
        self._uid = uid

    @property
    def _appliance(self):
        return self.coordinator.data.get(self._uid)

    @property
    def device_info(self) -> DeviceInfo:
        appliance = self._appliance
        name = ""
        model = ""
        if appliance:
            name = appliance.additional_name or appliance.name
            model = appliance.device_type
        return DeviceInfo(
            identifiers={(DOMAIN, self._uid)},
            name=name,
            manufacturer="Miele",
            model=model,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._appliance is not None
