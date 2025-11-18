"""Climate for Electrolux Group Integration."""

import logging
from typing import Any

from electrolux_group_developer_sdk.client.appliances.ac_appliance import ACAppliance
from electrolux_group_developer_sdk.client.appliances.dam_ac_appliance import (
    DAMACAppliance,
)
from electrolux_group_developer_sdk.constants import (
    APPLIANCE_STATE_IDLE,
    APPLIANCE_STATE_OFF,
)

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_FOCUS,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper
from .util import round_to_valid_step

_LOGGER = logging.getLogger(__name__)

ELECTROLUX_TO_HA_MODES = {
    "HEAT": HVACMode.HEAT,
    "COOL": HVACMode.COOL,
    "AUTO": HVACMode.AUTO,
    "DRY": HVACMode.DRY,
    "FANONLY": HVACMode.FAN_ONLY,
    "OFF": HVACMode.OFF,
    # ECO is missing
}

ELECTROLUX_DAM_TO_HA_MODES = {
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
    "auto": HVACMode.AUTO,
    "dry": HVACMode.DRY,
    "fanOnly": HVACMode.FAN_ONLY,
    "off": HVACMode.OFF,
    # ECO is missing
}

HA_TO_ELECTROLUX_MODES = {v: k for k, v in ELECTROLUX_TO_HA_MODES.items()}
HA_TO_ELECTROLUX_DAM_MODES = {v: k for k, v in ELECTROLUX_DAM_TO_HA_MODES.items()}

ELECTROLUX_TO_HA_FAN_SPEEDS = {
    "LOW": FAN_LOW,
    "MIDDLE": FAN_MEDIUM,
    "HIGH": FAN_HIGH,
    "TURBO": FAN_FOCUS,
    "AUTO": FAN_AUTO,
}

ELECTROLUX_DAM_TO_HA_FAN_SPEEDS = {
    "low": FAN_LOW,
    "medium": FAN_MEDIUM,
    "high": FAN_HIGH,
    "turbo": FAN_FOCUS,
    "auto": FAN_AUTO,
}

HA_TO_ELECTROLUX_FAN_SPEEDS = {v: k for k, v in ELECTROLUX_TO_HA_FAN_SPEEDS.items()}

HA_TO_ELECTROLUX_DAM_FAN_SPEEDS = {
    v: k for k, v in ELECTROLUX_DAM_TO_HA_FAN_SPEEDS.items()
}

ELECTROLUX_TO_HA_TEMPERATURE_UNIT = {
    "CELSIUS": UnitOfTemperature.CELSIUS,
    "FAHRENHEIT": UnitOfTemperature.FAHRENHEIT,
}


def build_entities_for_appliance(
    appliance_data, coordinators
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities: list[ElectroluxBaseEntity] = []

    if isinstance(appliance_data, ACAppliance):
        entities.append(
            ElectroluxClimateEntity(
                appliance_data=appliance_data,
                coordinator=coordinator,
            )
        )

    if isinstance(appliance_data, DAMACAppliance):
        entities.append(
            ElectroluxDamClimateEntity(
                appliance_data=appliance_data, coordinator=coordinator
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set Climate entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class ElectroluxClimateEntity(ElectroluxBaseEntity[ACAppliance], ClimateEntity):
    """Representation of an Electrolux AC unit."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.FAN_MODE
    )

    def __init__(
        self, appliance_data: ACAppliance, coordinator: ElectroluxDataUpdateCoordinator
    ) -> None:
        """Initialize the climate device."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Climate"
        self._attr_hvac_modes = self._get_hvac_supported_mode()
        self._attr_fan_modes = self._get_fan_supported_mode()

        self._update_attr_state()

    def _update_attr_state(self) -> None:
        # Set current mode
        self._attr_hvac_mode = self._get_hvac_mode()

        # Set temperature
        self._attr_temperature_unit = self._get_temperature_unit()
        self._attr_current_temperature = self._get_ambient_temperature()
        self._attr_target_temperature = self._get_target_temperature()
        self._attr_max_temp = self._appliance_data.get_supported_max_temp()
        self._attr_min_temp = self._appliance_data.get_supported_min_temp()
        self.target_temperature_step = self._appliance_data.get_supported_step_temp()

        # Set fan speed
        self._attr_fan_mode = self._get_fan_speed()

    def _get_hvac_supported_mode(self) -> list[HVACMode]:
        available_modes = self._appliance_data.get_supported_modes()
        hvac_modes: list[HVACMode] = [
            ELECTROLUX_TO_HA_MODES[mode.upper()]
            for mode in available_modes
            if mode in ELECTROLUX_TO_HA_MODES
        ]
        if HVACMode.OFF not in hvac_modes:
            hvac_modes.append(HVACMode.OFF)
        return hvac_modes

    def _get_fan_supported_mode(self) -> list[str]:
        available_fan_modes = self._appliance_data.get_supported_fan_speeds()
        fan_modes: list[str] = [
            ELECTROLUX_TO_HA_FAN_SPEEDS[fan_mode.upper()]
            for fan_mode in available_fan_modes
            if fan_mode in ELECTROLUX_TO_HA_FAN_SPEEDS
        ]
        return fan_modes

    def _get_hvac_mode(self) -> HVACMode | None:
        """Return hvac target mode."""
        current_appliance_state = self._appliance_data.get_current_appliance_state()
        if current_appliance_state and current_appliance_state.upper() in (
            APPLIANCE_STATE_OFF,
            APPLIANCE_STATE_IDLE,
        ):
            return HVACMode.OFF

        current_mode = self._appliance_data.get_current_mode()
        if current_mode:
            return ELECTROLUX_TO_HA_MODES.get(current_mode.upper())
        return None

    def _get_fan_speed(self) -> str | None:
        """Return fan speed."""
        current_fan_speed = self._appliance_data.get_current_fan_speed()
        if current_fan_speed:
            return ELECTROLUX_TO_HA_FAN_SPEEDS.get(current_fan_speed.upper())
        return None

    def _get_temperature_unit(self) -> UnitOfTemperature:
        """Return current temperature unit. Return Celsius as default."""
        return ELECTROLUX_TO_HA_TEMPERATURE_UNIT.get(
            self._appliance_data.get_current_temperature_unit(),
            UnitOfTemperature.CELSIUS,
        )

    def _get_target_temperature(self) -> float | None:
        """Return current target temperature."""
        if self._attr_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            return self._appliance_data.get_current_target_temperature_f()

        return self._appliance_data.get_current_target_temperature_c()

    def _get_ambient_temperature(self) -> float | None:
        """Return current ambient temperature."""
        if self._attr_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            return self._appliance_data.get_current_ambient_temperature_f()

        return self._appliance_data.get_current_ambient_temperature_c()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Handle changing fan mode."""
        command = self._appliance_data.get_fan_speed_command(
            HA_TO_ELECTROLUX_FAN_SPEEDS[fan_mode]
        )
        await self.send_device_command(command)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Handle changing HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self._turn_off_appliance()
        else:
            await self._set_appliance_mode(hvac_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        rounded_temperature = round_to_valid_step(
            temperature,
            self._attr_min_temp,
            self.target_temperature_step,  # type: ignore  # noqa: PGH003
        )
        if self._attr_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            command = self._appliance_data.get_temperature_f_command(
                rounded_temperature
            )
        else:
            command = self._appliance_data.get_temperature_c_command(
                rounded_temperature
            )

        await self.send_device_command(command)

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self._turn_on_appliance()

    async def async_turn_off(self) -> None:
        """Turn device off."""
        await self._turn_off_appliance()

    async def _turn_on_appliance(self) -> None:
        command = self._appliance_data.get_turn_on_command()
        await self.send_device_command(command)

    async def _turn_off_appliance(self) -> None:
        command = self._appliance_data.get_turn_off_command()
        await self.send_device_command(command)

    async def _set_appliance_mode(self, mode: HVACMode) -> None:
        current_mode = self._appliance_data.get_current_mode()
        current_appliance_state = self._appliance_data.get_current_appliance_state()
        if (
            current_mode
            and ELECTROLUX_TO_HA_MODES.get(current_mode) == mode
            and current_appliance_state.upper() == APPLIANCE_STATE_OFF
        ):
            command = self._appliance_data.get_turn_on_command()
        elif current_appliance_state.upper() == APPLIANCE_STATE_OFF:
            command = (
                self._appliance_data.get_turn_on_command()
                | self._appliance_data.get_mode_command(HA_TO_ELECTROLUX_MODES[mode])
            )
        else:
            command = self._appliance_data.get_mode_command(
                HA_TO_ELECTROLUX_MODES[mode]
            )
        await self.send_device_command(command)


class ElectroluxDamClimateEntity(ElectroluxBaseEntity[DAMACAppliance], ClimateEntity):
    """Representation of an Electrolux DAM AC unit."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.FAN_MODE
    )

    def __init__(
        self,
        appliance_data: DAMACAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the climate device."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Climate"
        self._attr_hvac_modes = self._get_hvac_supported_mode()
        self._attr_fan_modes = self._get_fan_supported_mode()

        self._update_attr_state()

    def _update_attr_state(self) -> None:
        # Set current mode
        self._attr_hvac_mode = self._get_hvac_mode()

        # Set temperature
        self._attr_temperature_unit = self._get_temperature_unit()
        self._attr_current_temperature = self._get_ambient_temperature()
        self._attr_target_temperature = self._get_target_temperature()
        self._attr_max_temp = self._appliance_data.get_supported_max_temp()
        self._attr_min_temp = self._appliance_data.get_supported_min_temp()
        self.target_temperature_step = self._appliance_data.get_supported_step_temp()

        # Set fan speed
        self._attr_fan_mode = self._get_fan_speed()

    def _get_hvac_supported_mode(self) -> list[HVACMode]:
        available_modes = self._appliance_data.get_supported_modes()
        hvac_modes: list[HVACMode] = [
            ELECTROLUX_DAM_TO_HA_MODES[mode]
            for mode in available_modes
            if mode in ELECTROLUX_DAM_TO_HA_MODES
        ]
        if HVACMode.OFF not in hvac_modes:
            hvac_modes.append(HVACMode.OFF)
        return hvac_modes

    def _get_fan_supported_mode(self) -> list[str]:
        available_fan_modes = self._appliance_data.get_supported_fan_speeds()
        fan_modes: list[str] = [
            ELECTROLUX_DAM_TO_HA_FAN_SPEEDS[fan_mode]
            for fan_mode in available_fan_modes
            if fan_mode in ELECTROLUX_DAM_TO_HA_FAN_SPEEDS
        ]
        return fan_modes

    def _get_hvac_mode(self) -> HVACMode | None:
        """Return hvac target mode."""
        current_appliance_state = self._appliance_data.get_current_appliance_state()
        if current_appliance_state and current_appliance_state.upper() in (
            APPLIANCE_STATE_OFF,
            APPLIANCE_STATE_IDLE,
        ):
            return HVACMode.OFF

        current_mode = self._appliance_data.get_current_mode()
        if current_mode:
            return ELECTROLUX_DAM_TO_HA_MODES.get(current_mode)
        return None

    def _get_fan_speed(self) -> str | None:
        """Return fan speed."""
        current_fan_speed = self._appliance_data.get_current_fan_speed()
        if current_fan_speed:
            return ELECTROLUX_DAM_TO_HA_FAN_SPEEDS.get(current_fan_speed)
        return None

    def _get_temperature_unit(self) -> UnitOfTemperature:
        """Return current temperature unit. Return Celsius as default."""
        return ELECTROLUX_TO_HA_TEMPERATURE_UNIT.get(
            self._appliance_data.get_current_temperature_unit(),
            UnitOfTemperature.CELSIUS,
        )

    def _get_target_temperature(self) -> float | None:
        """Return current target temperature."""
        return self._appliance_data.get_current_target_temperature()

    def _get_ambient_temperature(self) -> float | None:
        """Return current ambient temperature."""
        return self._appliance_data.get_current_ambient_temperature()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Handle changing fan mode."""
        command = self._appliance_data.get_fan_speed_command(
            HA_TO_ELECTROLUX_DAM_FAN_SPEEDS[fan_mode]
        )
        await self.send_device_command(command)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Handle changing HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self._turn_off_appliance()
        else:
            await self._set_appliance_mode(hvac_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        rounded_temperature = round_to_valid_step(
            temperature,
            self._attr_min_temp,
            self.target_temperature_step,  # type: ignore  # noqa: PGH003
        )
        command = self._appliance_data.get_temperature_command(rounded_temperature)
        await self.send_device_command(command)

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self._turn_on_appliance()

    async def async_turn_off(self) -> None:
        """Turn device off."""
        await self._turn_off_appliance()

    async def _turn_on_appliance(self) -> None:
        command = self._appliance_data.get_turn_on_command()
        await self.send_device_command(command)

    async def _turn_off_appliance(self) -> None:
        command = self._appliance_data.get_turn_off_command()
        await self.send_device_command(command)

    async def _set_appliance_mode(self, mode: HVACMode) -> None:
        current_mode = self._appliance_data.get_current_mode()
        current_appliance_state = self._appliance_data.get_current_appliance_state()
        if (
            current_mode
            and ELECTROLUX_DAM_TO_HA_MODES.get(current_mode) == mode
            and current_appliance_state.upper() == APPLIANCE_STATE_OFF
        ):
            command = self._appliance_data.get_turn_on_command()
        elif current_appliance_state.upper() == APPLIANCE_STATE_OFF:
            turn_on = self._appliance_data.get_turn_on_command()
            mode_cmd = self._appliance_data.get_mode_command(
                HA_TO_ELECTROLUX_DAM_MODES.get(mode)
            )

            command = {
                "airConditioner": {
                    **turn_on.get("airConditioner", {}),
                    **mode_cmd.get("airConditioner", {}),
                }
            }
        else:
            command = self._appliance_data.get_mode_command(
                HA_TO_ELECTROLUX_MODES.get(mode)
            )
        await self.send_device_command(command)
