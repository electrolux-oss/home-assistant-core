"""Switch entity for Electrolux Group Integration."""

import logging
from typing import Any, TypeVar, cast

from electrolux_group_developer_sdk.client.appliances.hb_appliance import HBAppliance
from electrolux_group_developer_sdk.client.appliances.ov_appliance import OVAppliance
from electrolux_group_developer_sdk.client.appliances.so_appliance import SOAppliance
from electrolux_group_developer_sdk.constants import (
    RC_ENABLED,
    RC_NOT_SAFETY_RELEVANT_ENABLED,
)
from electrolux_group_developer_sdk.feature_constants import CAVITY_LIGHT, CHILD_LOCK

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper

_LOGGER = logging.getLogger(__name__)


def build_entities_for_appliance(
    appliance_data, coordinators
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities: list[ElectroluxBaseEntity] = []

    if isinstance(appliance_data, OVAppliance):
        if appliance_data.is_feature_supported(CAVITY_LIGHT):
            entities.append(
                CavityLightEntity(
                    appliance_data=appliance_data, coordinator=coordinator
                )
            )

    if isinstance(appliance_data, SOAppliance):
        entities.extend(
            CavityLightEntity(appliance_data, coordinator, cavity)
            for cavity in appliance_data.get_supported_cavities()
            if appliance_data.is_cavity_feature_supported(cavity, CAVITY_LIGHT)
        )

    if isinstance(appliance_data, HBAppliance):
        if appliance_data.is_feature_supported(CHILD_LOCK):
            entities.append(
                ChildLockEntity(appliance_data=appliance_data, coordinator=coordinator)
            )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set Switch entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


T = TypeVar("T", OVAppliance, SOAppliance)


class CavityLightEntity(ElectroluxBaseEntity[T], SwitchEntity):
    """Representation of an Electrolux oven cavity light switch."""

    def __init__(
        self,
        appliance_data: T,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity: str | None = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(appliance_data, coordinator)
        self._cavity = cavity
        self._attr_name = "Light" if self._cavity is None else f"{cavity} - light"
        self._attr_icon = "mdi:lightbulb-outline"
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_light"
            if self._cavity is None
            else f"{appliance_data.appliance.applianceId}_{cavity}_light"
        )
        self._appliance = cast(SOAppliance | OVAppliance, appliance_data)
        self._update_attr_state()

    def _update_attr_state(self):
        if isinstance(self._appliance, OVAppliance):
            self._attr_is_on = self._appliance.get_current_cavity_light()
        elif isinstance(self._appliance, SOAppliance):
            self._attr_is_on = self._appliance.get_current_cavity_cavity_light(
                self._cavity
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        command = None
        if isinstance(self._appliance, OVAppliance):
            command = self._appliance.get_cavity_light_command(True)
        elif isinstance(self._appliance, SOAppliance):
            command = self._appliance.get_cavity_light_command(self._cavity, True)
        await self.send_device_command(command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        command = None
        if isinstance(self._appliance, OVAppliance):
            command = self._appliance.get_cavity_light_command(False)
        elif isinstance(self._appliance, SOAppliance):
            command = self._appliance.get_cavity_light_command(self._cavity, False)
        await self.send_device_command(command)


class ChildLockEntity(ElectroluxBaseEntity[HBAppliance], SwitchEntity):
    """Representation of an Electrolux child lock switch."""

    def __init__(
        self,
        appliance_data: HBAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Child lock"
        self._attr_icon = "mdi:lock"
        self._attr_unique_id = f"{appliance_data.appliance.applianceId}_childLock"
        self._update_attr_state()

    @property
    def available(self) -> bool:
        """True if the selector is available."""
        return self._appliance_data.get_current_remote_control() in (
            RC_ENABLED,
            RC_NOT_SAFETY_RELEVANT_ENABLED,
        )

    def _update_attr_state(self):
        self._attr_is_on = self._appliance_data.get_current_child_lock()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the child lock on."""
        await self.send_device_command(
            self._appliance_data.get_enable_child_lock_command()
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the child lock off is not possible remotely."""
        _LOGGER.warning("The child lock cannot be turned off remotely")
