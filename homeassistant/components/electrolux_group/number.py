"""Number entity for Electrolux Group Integration."""

import logging
from typing import TypeVar, cast

from electrolux_group_developer_sdk.appliance_config.cr_config import FREEZER, FRIDGE
from electrolux_group_developer_sdk.client.appliances.cr_appliance import CRAppliance
from electrolux_group_developer_sdk.client.appliances.hd_appliance import HDAppliance
from electrolux_group_developer_sdk.client.appliances.ov_appliance import OVAppliance
from electrolux_group_developer_sdk.client.appliances.so_appliance import SOAppliance
from electrolux_group_developer_sdk.feature_constants import (
    LIGHT_COLOR_TEMPERATURE,
    LIGHT_INTENSITY,
    TARGET_DURATION,
    TARGET_TEMPERATURE_C,
    TARGET_TEMPERATURE_F,
)

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper
from .util import round_to_valid_step

_LOGGER = logging.getLogger(__name__)

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

    if isinstance(appliance_data, OVAppliance):
        entities.extend(
            cls(appliance_data, coordinator)
            for cls in (OvenTemperatureEntity, OvenDurationEntity)
            if appliance_data.is_feature_supported(ENTITY_FEATURE_MAP.get(cls))
        )

    if isinstance(appliance_data, CRAppliance):
        target_temperature_cavities = [FRIDGE, FREEZER]
        cavities = [
            cavity
            for cavity in appliance_data.get_supported_cavities()
            if cavity in target_temperature_cavities
            if appliance_data.is_cavity_feature_supported(
                cavity, ENTITY_FEATURE_MAP[RefrigeratorTemperatureEntity]
            )
        ]

        entities.extend(
            RefrigeratorTemperatureEntity(appliance_data, coordinator, cavity)
            for cavity in cavities
        )

    if isinstance(appliance_data, HDAppliance):
        entities.extend(
            cls(appliance_data, coordinator)
            for cls in (HoodLightIntensityEntity, HoodLightColorTemperatureEntity)
            if appliance_data.is_feature_supported(ENTITY_FEATURE_MAP.get(cls))
        )

    if isinstance(appliance_data, SOAppliance):
        entities.extend(
            cls(appliance_data, coordinator, cavity)
            for cls in (OvenTemperatureEntity, OvenDurationEntity)
            for cavity in appliance_data.get_supported_cavities()
            if appliance_data.is_cavity_feature_supported(
                cavity, ENTITY_FEATURE_MAP.get(cls)
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set Number entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


T = TypeVar("T", OVAppliance, SOAppliance)


class OvenTemperatureEntity(ElectroluxBaseEntity[T], NumberEntity):
    """Representation of an Electrolux temperature selection."""

    def __init__(
        self,
        appliance_data: T,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity: str | None = None,
    ) -> None:
        """Initialize the number box."""
        super().__init__(appliance_data, coordinator)
        self._cavity = cavity

        self._attr_name = (
            "Target temperature"
            if self._cavity is None
            else f"{cavity} - target temperature"
        )
        self._attr_icon = "mdi:thermometer"
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_temperature"
            if self._cavity is None
            else f"{appliance_data.appliance.applianceId}_{cavity}_temperature"
        )
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._appliance = cast(
            OVAppliance | SOAppliance,
            self._appliance_data,
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_unit_of_measurement = ELECTROLUX_TO_HA_TEMPERATURE_UNIT.get(
            self._appliance.get_current_temperature_unit(),
            UnitOfTemperature.CELSIUS,
        )
        self._attr_native_value = self._get_target_temperature()
        self._attr_available = self._is_number_available()
        if isinstance(self._appliance, OVAppliance):
            self._attr_native_min_value = self._appliance.get_supported_min_temp()
            self._attr_native_max_value = self._appliance.get_supported_max_temp()
            self._attr_native_step = self._appliance.get_supported_step_temp()
        elif isinstance(self._appliance, SOAppliance):
            self._attr_native_min_value = self._appliance.get_cavity_supported_min_temp(
                self._cavity
            )
            self._attr_native_max_value = self._appliance.get_cavity_supported_max_temp(
                self._cavity
            )
            self._attr_native_step = self._appliance.get_cavity_supported_step_temp(
                self._cavity
            )

    @property
    def available(self) -> bool:
        "True if the options can be selected."
        return self._is_number_available()

    def _get_target_temperature(self) -> float:
        """Return current target temperature."""
        if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
            if isinstance(self._appliance, OVAppliance):
                return self._appliance.get_current_target_temperature_f()
            if isinstance(self._appliance, SOAppliance):
                return self._appliance.get_current_cavity_target_temperature_f(
                    self._cavity
                )

        if isinstance(self._appliance, OVAppliance):
            return self._appliance.get_current_target_temperature_c()
        if isinstance(self._appliance, SOAppliance):
            return self._appliance.get_current_cavity_target_temperature_c(self._cavity)
        return 0

    def _is_number_available(self) -> bool:
        current_program = None
        if isinstance(self._appliance, OVAppliance):
            current_program = self._appliance.get_current_program()
        if isinstance(self._appliance, SOAppliance):
            current_program = self._appliance.get_current_cavity_program(self._cavity)
        return (
            current_program is not None
            and self._appliance.get_current_remote_control() == "ENABLED"
        )

    async def async_set_native_value(self, value: float) -> None:
        """Send selected temperature to the appliance."""
        command = None

        rounded_value = round_to_valid_step(
            value, self._attr_native_min_value, self._attr_native_step
        )
        if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
            if isinstance(self._appliance, OVAppliance):
                command = self._appliance.get_temperature_f_command(rounded_value)
            if isinstance(self._appliance, SOAppliance):
                command = self._appliance.get_temperature_f_command(
                    self._cavity, rounded_value
                )
        else:
            if isinstance(self._appliance, OVAppliance):
                command = self._appliance.get_temperature_c_command(rounded_value)
            if isinstance(self._appliance, SOAppliance):
                command = self._appliance.get_temperature_c_command(
                    self._cavity, rounded_value
                )
        await self.send_device_command(command)


class OvenDurationEntity(ElectroluxBaseEntity[T], NumberEntity):
    """Representation of an Electrolux temperature selection."""

    def __init__(
        self,
        appliance_data: T,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity: str | None = None,
    ) -> None:
        """Initialize the number box."""
        super().__init__(appliance_data, coordinator)
        self._cavity = cavity
        self._attr_name = "Timer" if self._cavity is None else f"{cavity} - timer"
        self._attr_icon = "mdi:timer-outline"
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_timer"
            if self._cavity is None
            else f"{appliance_data.appliance.applianceId}_{cavity}_timer"
        )
        self._attr_device_class = NumberDeviceClass.DURATION
        self._appliance = cast(
            OVAppliance | SOAppliance,
            self._appliance_data,
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        if isinstance(self._appliance, OVAppliance):
            self._attr_native_value = (
                self._appliance.get_current_target_duration()
            ) // 60
            self._attr_native_min_value = (
                self._appliance.get_supported_min_duration()
            ) / 60
            self._attr_native_max_value = (
                self._appliance.get_supported_max_duration()
            ) / 60
            self._attr_native_step = (
                self._appliance.get_supported_step_duration()
            ) / 60
        elif isinstance(self._appliance, SOAppliance):
            self._attr_native_value = (
                self._appliance.get_current_cavity_target_duration(self._cavity)
            ) // 60
            self._attr_native_min_value = (
                self._appliance.get_cavity_supported_min_duration(self._cavity)
            ) / 60
            self._attr_native_max_value = (
                self._appliance.get_cavity_supported_max_duration(self._cavity)
            ) / 60
            self._attr_native_step = (
                self._appliance.get_cavity_supported_step_duration(self._cavity)
            ) / 60

        self._attr_available = self._is_number_available()

    @property
    def available(self) -> bool:
        "True if the options can be selected."
        return self._is_number_available()

    def _is_number_available(self) -> bool:
        current_program = None
        if isinstance(self._appliance, OVAppliance):
            current_program = self._appliance.get_current_program()
        elif isinstance(self._appliance, SOAppliance):
            current_program = self._appliance.get_current_cavity_program(self._cavity)
        return (
            current_program is not None
            and self._appliance_data.get_current_remote_control() == "ENABLED"
        )

    async def async_set_native_value(self, value: float) -> None:
        """Send selected duration to the appliance."""
        seconds = int(value * 60)
        command = None

        if isinstance(self._appliance, OVAppliance):
            command = self._appliance.get_target_duration_command(seconds)
        elif isinstance(self._appliance, SOAppliance):
            command = self._appliance.get_target_duration_command(self._cavity, seconds)
        self._attr_native_value = seconds
        await self.send_device_command(command)


class HoodLightIntensityEntity(ElectroluxBaseEntity[HDAppliance], NumberEntity):
    """Representation of an Electrolux light intensity selection."""

    def __init__(
        self,
        appliance_data: HDAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the number box."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Light intensity"
        self._attr_icon = "mdi:lightbulb-outline"
        self._attr_unique_id = f"{appliance_data.appliance.applianceId}_light_intensity"
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_unit_of_measurement = "%"
        self._attr_native_value = self._appliance_data.get_current_light_intensity()
        self._attr_native_min_value = self._appliance_data.get_min_light_intensity()
        self._attr_native_max_value = self._appliance_data.get_max_light_intensity()
        self._attr_native_step = self._appliance_data.get_step_light_intensity()

    async def async_set_native_value(self, value: float) -> None:
        """Send selected intensity to the appliance."""
        command = self._appliance_data.get_set_light_intensity_command(round(value))
        await self.send_device_command(command)


class HoodLightColorTemperatureEntity(ElectroluxBaseEntity[HDAppliance], NumberEntity):
    """Representation of an Electrolux light color temperature selection."""

    def __init__(
        self,
        appliance_data: HDAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the number box."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Light color temperature"
        self._attr_icon = "mdi:lightbulb-outline"
        self._attr_unique_id = f"{appliance_data.appliance.applianceId}_light_color"
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_unit_of_measurement = "%"
        self._attr_native_value = (
            self._appliance_data.get_current_light_color_temperature()
        )
        self._attr_native_min_value = (
            self._appliance_data.get_min_light_color_temperature_range()
        )
        self._attr_native_max_value = (
            self._appliance_data.get_max_light_color_temperature_range()
        )
        self._attr_native_step = (
            self._appliance_data.get_step_light_color_temperature_range()
        )

    async def async_set_native_value(self, value: float) -> None:
        """Send selected color temperature to the appliance."""
        command = self._appliance_data.get_set_light_color_temperature_command(
            round(value)
        )
        await self.send_device_command(command)


class RefrigeratorTemperatureEntity(ElectroluxBaseEntity[CRAppliance], NumberEntity):
    """Representation of an Electrolux CR temperature selection."""

    def __init__(
        self,
        appliance_data: CRAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity,
    ) -> None:
        """Initialize the number box."""
        super().__init__(appliance_data, coordinator)
        self._cavity = cavity
        self._attr_name = f"{cavity} - Target temperature"
        self._attr_icon = "mdi:thermometer"
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_temperature_{cavity}"
        )
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_unit_of_measurement = ELECTROLUX_TO_HA_TEMPERATURE_UNIT.get(
            self._appliance_data.get_current_temperature_unit(),
            UnitOfTemperature.CELSIUS,
        )
        self._attr_native_value = self._get_target_temperature()
        self._attr_native_min_value = (
            self._appliance_data.get_supported_min_temperature(self._cavity)
        )
        self._attr_native_max_value = (
            self._appliance_data.get_supported_max_temperature(self._cavity)
        )
        self._attr_native_step = self._appliance_data.get_supported_step_temperature(
            self._cavity
        )

    def _get_target_temperature(self) -> float:
        """Return current target temperature."""
        if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
            return self._appliance_data.get_current_cavity_target_temperature_f(
                self._cavity
            )

        return self._appliance_data.get_current_cavity_target_temperature_c(
            self._cavity
        )

    async def async_set_native_value(self, value: float) -> None:
        """Send selected temperature to the appliance."""

        rounded_value = round_to_valid_step(
            value, self._attr_native_min_value, self._attr_native_step
        )
        if self._attr_native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT:
            command = self._appliance_data.get_set_cavity_temperature_f_command(
                self._cavity, rounded_value
            )
        else:
            command = self._appliance_data.get_set_cavity_temperature_c_command(
                self._cavity, rounded_value
            )
        await self.send_device_command(command)


# Map entity classes to feature constants
ENTITY_FEATURE_MAP = {
    OvenTemperatureEntity: [TARGET_TEMPERATURE_C, TARGET_TEMPERATURE_F],
    OvenDurationEntity: TARGET_DURATION,
    HoodLightIntensityEntity: LIGHT_INTENSITY,
    HoodLightColorTemperatureEntity: LIGHT_COLOR_TEMPERATURE,
    RefrigeratorTemperatureEntity: [TARGET_TEMPERATURE_C, TARGET_TEMPERATURE_F],
}
