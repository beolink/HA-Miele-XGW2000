"""Sensor platform for Miele XGW 2000."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MieleCoordinator
from .entity import MieleEntity


@dataclass(frozen=True)
class MieleSensorDescription(SensorEntityDescription):
    value_fn: Callable | None = None


# Sensors derived from the base device list
BASE_SENSORS: tuple[MieleSensorDescription, ...] = (
    MieleSensorDescription(
        key="state",
        name="Status",
        icon="mdi:washing-machine",
        value_fn=lambda a: a.state,
    ),
)

# Sensors derived from the detail info keys
INFO_SENSORS: tuple[MieleSensorDescription, ...] = (
    MieleSensorDescription(
        key="program",
        name="Program",
        icon="mdi:playlist-play",
        value_fn=lambda a: a.info.get("program") or a.info.get("selectedProgram"),
    ),
    MieleSensorDescription(
        key="phase",
        name="Phase",
        icon="mdi:progress-clock",
        value_fn=lambda a: a.info.get("phase") or a.info.get("programPhase"),
    ),
    MieleSensorDescription(
        key="remaining_time",
        name="Remaining time",
        icon="mdi:timer-outline",
        native_unit_of_measurement="min",
        value_fn=lambda a: _parse_time(
            a.info.get("remainingTime") or a.info.get("remainingProgramTime")
        ),
    ),
    MieleSensorDescription(
        key="start_time",
        name="Start time",
        icon="mdi:clock-start",
        value_fn=lambda a: a.info.get("startTime"),
    ),
    MieleSensorDescription(
        key="end_time",
        name="End time",
        icon="mdi:clock-end",
        value_fn=lambda a: a.info.get("endTime"),
    ),
)


def _parse_time(value: str | None) -> int | None:
    """Convert 'H:MM' or integer string to minutes."""
    if not value:
        return None
    if ":" in value:
        parts = value.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return None
    try:
        return int(value)
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MieleCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MieleSensorEntity] = []

    for uid in coordinator.data:
        for desc in BASE_SENSORS + INFO_SENSORS:
            entities.append(MieleSensorEntity(coordinator, uid, desc))

    async_add_entities(entities)


class MieleSensorEntity(MieleEntity, SensorEntity):
    entity_description: MieleSensorDescription

    def __init__(
        self,
        coordinator: MieleCoordinator,
        uid: str,
        description: MieleSensorDescription,
    ) -> None:
        super().__init__(coordinator, uid)
        self.entity_description = description
        self._attr_unique_id = f"{uid}_{description.key}"

    @property
    def native_value(self):
        appliance = self._appliance
        if appliance is None:
            return None
        return self.entity_description.value_fn(appliance)
