"""RVC entity for Electrolux Group Integration."""

import logging
from typing import Any

from electrolux_group_developer_sdk.client.appliances.rvc_appliance import RVCAppliance

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper

_LOGGER = logging.getLogger(__name__)
VACUUM_ACTIVITY_MAP = {
    1: VacuumActivity.CLEANING,  # Cleaning
    2: VacuumActivity.PAUSED,  # PausedCleaning
    3: VacuumActivity.CLEANING,  # SpotCleaning
    4: VacuumActivity.PAUSED,  # PausedSpotCleaning
    5: VacuumActivity.RETURNING,  # Return
    6: VacuumActivity.PAUSED,  # PausedReturn
    7: VacuumActivity.RETURNING,  # ReturnForPitstop
    8: VacuumActivity.PAUSED,  # PausedReturnForPitstop
    9: VacuumActivity.DOCKED,  # Charging
    10: VacuumActivity.IDLE,  # Sleeping
    11: VacuumActivity.ERROR,  # Error
    12: VacuumActivity.DOCKED,  # Pitstop
    13: VacuumActivity.IDLE,  # ManualSteering
    14: VacuumActivity.IDLE,  # FWUpgrade
    "inProgress": VacuumActivity.CLEANING,
    "goingHome": VacuumActivity.RETURNING,
    "idle": VacuumActivity.IDLE,
    "paused": VacuumActivity.PAUSED,
    "sleeping": VacuumActivity.DOCKED,
}

ELECTROLUX_TO_HA_MODES = {
    1: "Quiet",
    2: "Smart",
    3: "Power",
    "energySaving": "Energy saving",
    "powerful": "Powerful",
    "quiet": "Quiet",
    "standard": "Standard",
    "maxPower": "Max power",
    "max": "Max",
}

HA_TO_ELECTROLUX_MODES = {v: k for k, v in ELECTROLUX_TO_HA_MODES.items()}


def build_entities_for_appliance(
    appliance_data, coordinators
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities: list[ElectroluxBaseEntity] = []

    if isinstance(appliance_data, RVCAppliance):
        entities.append(
            RvcEntity(appliance_data=appliance_data, coordinator=coordinator)
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set RVC entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class RvcEntity(ElectroluxBaseEntity[RVCAppliance], StateVacuumEntity):
    """Representation of an Electrolux RVC."""

    _attr_supported_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.SEND_COMMAND
    )

    def __init__(
        self,
        appliance_data: RVCAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the climate device."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "RVC"

        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_activity = self._get_current_activity()
        self._attr_fan_speed_list = self._get_available_modes()
        self._attr_fan_speed = self._get_current_mode()

    def _get_current_activity(self) -> VacuumActivity:
        if self._appliance_data.is_docked():
            return VacuumActivity.DOCKED

        reported_value = self._appliance_data.get_current_state()

        return VACUUM_ACTIVITY_MAP[reported_value] or VacuumActivity.IDLE

    def _get_current_mode(self) -> str:
        raw_mode = self._appliance_data.get_current_mode()
        mode = ELECTROLUX_TO_HA_MODES.get(raw_mode)
        if mode is None:
            _LOGGER.warning("Unmapped RVC mode found: %s", raw_mode)
            return "unknown"
        return mode

    def _get_available_modes(self) -> list[str]:
        modes = self._appliance_data.get_supported_modes()
        mapped_modes = []

        for mode in modes:
            readable = ELECTROLUX_TO_HA_MODES.get(mode)
            if readable is None:
                _LOGGER.warning("Unmapped RVC mode found: %s", mode)
                mapped_modes.append("unknown")
            else:
                mapped_modes.append(readable)

        return list(dict.fromkeys(mapped_modes))

    async def async_start(self, **kwargs: Any) -> None:
        """Start or resume the cleaning task."""
        if self._appliance_data.is_paused():
            command = self._appliance_data.get_resume_command()
        else:
            command = self._appliance_data.get_start_command()
        await self.send_device_command(command)

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner, do not return to base."""
        command = self._appliance_data.get_stop_command()
        await self.send_device_command(command)

    async def async_pause(self, **kwargs: Any) -> None:
        """Pause the cleaning task."""
        command = self._appliance_data.get_pause_command()
        await self.send_device_command(command)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        command = self._appliance_data.get_dock_command()
        await self.send_device_command(command)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set the fan speed."""
        command = self._appliance_data.get_set_mode_command(
            HA_TO_ELECTROLUX_MODES[fan_speed]
        )
        await self.send_device_command(command)

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle custom vacuum commands."""

        _LOGGER.debug("Received send_command: %s, params: %s", command, params)

        if command == "clean_zones" and isinstance(params, dict):
            map_id = params.get("map_id")
            zone_ids = params.get("zone_ids", []) if params else []
            power_mode = params.get("power_mode", 2)
            if map_id:
                await self._start_zone_clean(map_id, zone_ids, power_mode)
            else:
                _LOGGER.warning("Map id is missing")
        elif command == "clean_gordias_rooms" and isinstance(params, dict):
            map_id = params.get("map_id")
            room_ids = params.get("room_ids", []) if params else []
            sweep_mode = params.get("sweepMode", 0)
            vacuum_mode = params.get("vacuumMode", "standard")
            water_pump_rate = params.get("waterPumpRate", "off")
            repetitions = params.get("numberOfCleaningRepetitions", 1)
            if map_id:
                await self._start_gordias_room_clean(
                    map_id=map_id,
                    room_ids=room_ids,
                    sweep_mode=sweep_mode,
                    vacuum_mode=vacuum_mode,
                    water_pump_rate=water_pump_rate,
                    number_of_repetitions=repetitions,
                )
            else:
                _LOGGER.warning("Map id is missing")

        elif command == "clean_cybele_rooms" and isinstance(params, dict):
            map_id = params.get("map_id")
            room_ids_names = params.get("room_ids_names", []) if params else []
            global_settings_cleaning = params.get("globalSettingsCleaning", True)
            cleaning_type = params.get("cleaningType", "vacuum")
            vacuum_mode = params.get("vacuumMode", "standard")
            water_pump_rate = params.get("waterPumpRate", "off")
            repetitions = params.get("numberOfCleaningRepetitions", 1)
            if map_id:
                await self._start_cybele_room_clean(
                    map_id=map_id,
                    room_ids_names=room_ids_names,
                    global_settings_cleaning=global_settings_cleaning,
                    cleaning_type=cleaning_type,
                    vacuum_mode=vacuum_mode,
                    water_pump_rate=water_pump_rate,
                    number_of_repetitions=repetitions,
                )
            else:
                _LOGGER.warning("Map id is missing")
        else:
            _LOGGER.warning("Unknown command: %s", command)

    async def _start_zone_clean(
        self, map_id: str, zone_ids: list[str], power_mode: int = 2
    ) -> None:
        await self.send_device_command(
            self._appliance_data.get_start_zone_cleaning_command(
                map_id, zone_ids, power_mode
            )
        )

    async def _start_gordias_room_clean(
        self,
        map_id: int,
        room_ids: list[int],
        sweep_mode: int = 0,
        vacuum_mode="standard",
        water_pump_rate="off",
        number_of_repetitions=1,
    ) -> None:
        await self.send_device_command(
            self._appliance_data.get_gordias_start_room_cleaning_command(
                map_id,
                room_ids,
                sweep_mode,
                vacuum_mode,
                water_pump_rate,
                number_of_repetitions,
            )
        )

    async def _start_cybele_room_clean(
        self,
        map_id: int,
        room_ids_names: list[tuple[int, str]],
        global_settings_cleaning: bool = True,
        cleaning_type="vacuum",
        vacuum_mode="standard",
        water_pump_rate="off",
        number_of_repetitions=1,
    ) -> None:
        await self.send_device_command(
            self._appliance_data.get_cybele_start_room_cleaning_command(
                map_id,
                room_ids_names,
                global_settings_cleaning,
                cleaning_type,
                vacuum_mode,
                water_pump_rate,
                number_of_repetitions,
            )
        )
