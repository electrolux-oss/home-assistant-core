"""Fan entity for Electrolux Group Integration."""

import logging
from typing import Any

from electrolux_group_developer_sdk.client.appliances.ap_appliance import APAppliance
from electrolux_group_developer_sdk.client.appliances.dh_appliance import DHAppliance

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
from homeassistant.util.scaling import int_states_in_range

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper

_LOGGER = logging.getLogger(__name__)

ELECTROLUX_TO_HA_FAN_SPEEDS = {"LOW": 1, "MIDDLE": 2, "HIGH": 3}

HA_TO_ELECTROLUX_FAN_SPEEDS = {v: k for k, v in ELECTROLUX_TO_HA_FAN_SPEEDS.items()}


def build_entities_for_appliance(
    appliance_data, coordinators
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities: list[ElectroluxBaseEntity] = []

    if isinstance(appliance_data, DHAppliance):
        entities.append(
            DehumidifierFanEntity(
                appliance_data=appliance_data,
                coordinator=coordinator,
            )
        )

    if isinstance(appliance_data, APAppliance):
        entities.append(
            AirPurifierFanEntity(
                appliance_data=appliance_data,
                coordinator=coordinator,
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set Fan entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class DehumidifierFanEntity(ElectroluxBaseEntity[DHAppliance], FanEntity):
    """Representation of an Electrolux Dehumidifier fan unit."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    def __init__(
        self,
        appliance_data: DHAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the fan device."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Fan"
        self._speed_range = self._get_speed_range()
        self._attr_speed_count = int_states_in_range(self._speed_range)
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_is_on = self._is_dh_on()
        self._attr_percentage = self._get_current_fan_speed_percentage()

    def _get_current_fan_speed_percentage(self) -> int:
        """Return current fan speed."""
        return ranged_value_to_percentage(self._speed_range, self._get_current_speed())

    def _is_dh_on(self) -> bool:
        """Return true if the appliance is on."""
        return self._appliance_data.is_appliance_on()

    def _get_current_speed(self) -> int:
        """Return current fan speed."""
        if not self._is_dh_on():
            return 0

        return ELECTROLUX_TO_HA_FAN_SPEEDS[self._appliance_data.get_current_fan_speed()]

    def _get_speed_range(self):
        supported_fan_speeds = self._appliance_data.get_supported_fan_speeds()

        if not supported_fan_speeds:
            return (0, 0)

        values_count = len(supported_fan_speeds)
        if values_count > 0:
            return (1, values_count)
        return (0, 0)

    async def async_set_percentage(self, percentage: int) -> None:
        """Send set fan speed command."""
        fan_speed = round(
            percentage_to_ranged_value(
                percentage=percentage, low_high_range=self._get_speed_range()
            )
        )
        if fan_speed == 0:
            await self.async_turn_off()
        else:
            command = self._appliance_data.get_fan_speed_command(
                HA_TO_ELECTROLUX_FAN_SPEEDS[fan_speed]
            )
            await self.send_device_command(command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Send turn off command."""
        command = self._appliance_data.get_turn_off_command()
        await self.send_device_command(command)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Send turn on command."""
        command = self._appliance_data.get_turn_on_command()
        await self.send_device_command(command)


class AirPurifierFanEntity(ElectroluxBaseEntity[APAppliance], FanEntity):
    """Representation of an Electrolux Air purifier unit."""

    _attr_supported_features = (
        FanEntityFeature.PRESET_MODE
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    def __init__(
        self,
        appliance_data: APAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the fan device."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Fan"
        self._attr_preset_modes = self._get_supported_mode()
        self._speed_range = self._get_speed_range()
        self._attr_speed_count = int_states_in_range(self._speed_range)
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_is_on = self._is_ap_on()
        self._attr_percentage = self._get_current_fan_speed_percentage()
        self._attr_preset_mode = self._get_current_mode()

    def _is_ap_on(self) -> bool:
        """Return true if the appliance is on."""
        return self._appliance_data.is_appliance_on()

    def _get_current_fan_speed_percentage(self) -> int:
        """Return current fan speed if the appliance is on."""
        if self._is_ap_on():
            return ranged_value_to_percentage(
                self._speed_range, self._get_current_speed()
            )
        return 0

    def _get_current_speed(self) -> int:
        """Return current fan speed."""
        return self._appliance_data.get_current_fan_speed() or 0

    def _get_current_mode(self) -> str | None:
        """Return current mode, if the appliance is on."""
        if self._is_ap_on():
            return self._appliance_data.get_current_mode().capitalize()
        return None

    def _get_supported_mode(self) -> list[str]:
        """Return the supported modes."""
        modes = self._appliance_data.get_supported_modes() or []

        return [
            key.capitalize()
            for key in modes
            if key != self._appliance_data.get_off_mode()
        ]

    def _get_speed_range(self):
        """Return the supported fan speed ranges."""
        min_range = self._appliance_data.get_supported_min_fan_speed()
        max_range = self._appliance_data.get_supported_max_fan_speed()

        if not min_range or not max_range:
            return (0, 0)

        if min_range == 0:
            min_range += 1
        return (
            min_range,
            max_range,
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Send set mode command."""
        command = self._appliance_data.get_mode_command(preset_mode)
        await self.send_device_command(command)

    async def async_set_percentage(self, percentage: int) -> None:
        """Send set fan speed command. If fan speed percentage is 0 turn off the appliance."""
        fan_speed = round(
            percentage_to_ranged_value(
                percentage=percentage, low_high_range=self._get_speed_range()
            )
        )
        if fan_speed == 0:
            await self.async_turn_off()
        else:
            command = self._appliance_data.get_fan_speed_command(fan_speed)
            await self.send_device_command(command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Send turn off command."""
        command = self._appliance_data.get_turn_off_command()
        await self.send_device_command(command)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Send turn on command."""
        command = self._appliance_data.get_turn_on_command()
        await self.send_device_command(command)
