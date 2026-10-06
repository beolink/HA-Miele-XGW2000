"""Sensor platform for Miele XGW 2000."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MieleAppliance
from .const import DOMAIN
from .coordinator import MieleCoordinator
from .entity import MieleEntity


def _info(appliance: MieleAppliance, *keys: str) -> str | None:
    """Return the first non-empty info value among keys.

    The gateway uses human-readable names in the language of the detail URL
    ("Remaining Time" with language=en); older docs use camelCase
    ("remainingTime"). Accept both.
    """
    for key in keys:
        value = appliance.info.get(key)
        if value is not None and value.strip():
            return value.strip()
    return None


@dataclass(frozen=True)
class MieleSensorDescription(SensorEntityDescription):
    value_fn: Callable | None = None
    # Info keys this sensor reads; the sensor is only created when the
    # appliance reports one of them. Empty means always create.
    info_keys: tuple[str, ...] = ()


INVALID_TEMPERATURE = -30.0

PROGRAM_KEYS = ("Program", "program", "selectedProgram")
PHASE_KEYS = ("Phase", "phase", "programPhase")
REMAINING_KEYS = ("Remaining Time", "remainingTime", "remainingProgramTime")
START_KEYS = ("Start Time", "startTime")
END_KEYS = ("End Time", "endTime")
DURATION_KEYS = ("Duration", "duration")
TEMPERATURE_KEYS = ("Temperature", "temperature")
CORE_TEMPERATURE_KEYS = ("Core Temperature", "coreTemperature")
FUNCTION_KEYS = ("Cooking Function",)

SENSORS: tuple[MieleSensorDescription, ...] = (
    MieleSensorDescription(
        key="state",
        name="Status",
        icon="mdi:information-outline",
        # Base list <state> is a numeric code; the info "State" is the text
        value_fn=lambda a: _info(a, "State", "state") or a.state,
    ),
    MieleSensorDescription(
        key="program",
        name="Program",
        icon="mdi:playlist-play",
        info_keys=PROGRAM_KEYS,
        value_fn=lambda a: _info(a, *PROGRAM_KEYS),
    ),
    MieleSensorDescription(
        key="cooking_function",
        name="Cooking function",
        icon="mdi:stove",
        info_keys=FUNCTION_KEYS,
        value_fn=lambda a: _info(a, *FUNCTION_KEYS),
    ),
    MieleSensorDescription(
        key="phase",
        name="Phase",
        icon="mdi:progress-clock",
        info_keys=PHASE_KEYS,
        value_fn=lambda a: _info(a, *PHASE_KEYS),
    ),
    MieleSensorDescription(
        key="remaining_time",
        name="Remaining time",
        icon="mdi:timer-outline",
        native_unit_of_measurement="min",
        info_keys=REMAINING_KEYS,
        value_fn=lambda a: _parse_time(_info(a, *REMAINING_KEYS)),
    ),
    MieleSensorDescription(
        key="duration",
        name="Duration",
        icon="mdi:timer-sand",
        native_unit_of_measurement="min",
        info_keys=DURATION_KEYS,
        value_fn=lambda a: _parse_time(_info(a, *DURATION_KEYS)),
    ),
    MieleSensorDescription(
        key="start_time",
        name="Start time",
        icon="mdi:clock-start",
        info_keys=START_KEYS,
        value_fn=lambda a: _info(a, *START_KEYS),
    ),
    MieleSensorDescription(
        key="end_time",
        name="End time",
        icon="mdi:clock-end",
        info_keys=END_KEYS,
        value_fn=lambda a: _info(a, *END_KEYS),
    ),
    MieleSensorDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        info_keys=TEMPERATURE_KEYS,
        value_fn=lambda a: _parse_temperature(_info(a, *TEMPERATURE_KEYS)),
    ),
    MieleSensorDescription(
        key="core_temperature",
        name="Core temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        info_keys=CORE_TEMPERATURE_KEYS,
        value_fn=lambda a: _parse_temperature(_info(a, *CORE_TEMPERATURE_KEYS)),
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


def _parse_temperature(value: str | None) -> float | None:
    """Convert '180 °C' to 180.0."""
    if not value:
        return None
    try:
        temperature = float(value.split()[0].replace(",", "."))
    except (ValueError, IndexError):
        return None
    # The gateway reports -30 °C when it has no reading (oven off)
    if temperature <= INVALID_TEMPERATURE:
        return None
    return temperature


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MieleCoordinator = hass.data[DOMAIN][entry.entry_id]
    added: set[tuple[str, str]] = set()

    @callback
    def _add_new() -> None:
        # Appliances drop off and rejoin the powerline bus (the gateway can
        # list none at all), so add sensors as appliances and values appear.
        entities: list[MieleSensorEntity] = []
        for uid, appliance in (coordinator.data or {}).items():
            for desc in SENSORS:
                if (uid, desc.key) in added:
                    continue
                if desc.info_keys and not any(k in appliance.info for k in desc.info_keys):
                    continue
                added.add((uid, desc.key))
                entities.append(MieleSensorEntity(coordinator, uid, desc))
        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


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
