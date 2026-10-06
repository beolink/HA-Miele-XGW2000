"""Button platform for Miele XGW 2000 — Start / Stop actions."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MieleApiError
from .const import DOMAIN
from .coordinator import MieleCoordinator
from .entity import MieleEntity

_LOGGER = logging.getLogger(__name__)

# Map action names from the gateway to human-readable HA button names
ACTION_LABELS: dict[str, str] = {
    "start": "Start",
    "stop": "Stop",
    "pause": "Pause",
    "supercooling_on": "SuperCooling on",
    "supercooling_off": "SuperCooling off",
    "superfreezing_on": "SuperFreezing on",
    "superfreezing_off": "SuperFreezing off",
}

ACTION_ICONS: dict[str, str] = {
    "start": "mdi:play",
    "stop": "mdi:stop",
    "pause": "mdi:pause",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MieleCoordinator = hass.data[DOMAIN][entry.entry_id]
    added: set[tuple[str, str]] = set()

    @callback
    def _add_new() -> None:
        # Appliances drop off and rejoin the powerline bus, and actions are
        # only offered in some states, so add buttons as they first appear.
        entities: list[MieleActionButton] = []
        for uid, appliance in (coordinator.data or {}).items():
            for action in appliance.actions:
                # "Details" is the link to the detail XML, not something to press
                if action.name.lower() == "details" or (uid, action.name) in added:
                    continue
                if action.name in ACTION_LABELS or action.url:
                    added.add((uid, action.name))
                    entities.append(MieleActionButton(coordinator, uid, action.name, action.url))
        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class MieleActionButton(MieleEntity, ButtonEntity):
    def __init__(
        self,
        coordinator: MieleCoordinator,
        uid: str,
        action_name: str,
        action_url: str,
    ) -> None:
        super().__init__(coordinator, uid)
        self._action_name = action_name
        self._action_url = action_url
        self._attr_unique_id = f"{uid}_action_{action_name}"
        self._attr_name = ACTION_LABELS.get(action_name, action_name.replace("_", " ").title())
        self._attr_icon = ACTION_ICONS.get(action_name, "mdi:gesture-tap-button")

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        appliance = self._appliance
        if appliance is None:
            return False
        # Only available when the gateway exposes this action for the current state
        return any(a.name == self._action_name for a in appliance.actions)

    async def async_press(self) -> None:
        appliance = self._appliance
        if appliance is None:
            return
        # Use the current URL from coordinator data (may change with device state)
        action = next((a for a in appliance.actions if a.name == self._action_name), None)
        url = action.url if action else self._action_url
        try:
            await self.coordinator.api.trigger_action(url)
        except MieleApiError as exc:
            _LOGGER.error("Action %s failed for %s: %s", self._action_name, self._uid, exc)
            return
        await self.coordinator.async_refresh()
