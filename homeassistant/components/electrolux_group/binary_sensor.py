"""Sensor entity for Electrolux Group Integration."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from electrolux_group_developer_sdk.appliance_config.hd_config import (
    DRAWER_STATUS,
    HOOD_AUTO_SWITCH_OFF_EVENT,
)
from electrolux_group_developer_sdk.client.appliances.hd_appliance import HDAppliance

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ElectroluxBinarySensorDescription(BinarySensorEntityDescription):
    """Custom binary sensor description for Electrolux sensors."""

    is_supported_fn: Callable[[Any], Any] = lambda x: None
    value_fn: Callable[[Any], Any] = lambda x: None


HOOD_ELECTROLUX_SENSORS: tuple[ElectroluxBinarySensorDescription, ...] = (
    ElectroluxBinarySensorDescription(
        key="drawer_status",
        name="Drawer status",
        icon="mdi:file-cabinet",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(DRAWER_STATUS),
        value_fn=lambda appliance: appliance.get_current_drawer_status(),
    ),
    ElectroluxBinarySensorDescription(
        key="hood_auto_switch_off_event",
        name="Auto switch off event",
        icon="mdi:power-sleep",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            HOOD_AUTO_SWITCH_OFF_EVENT
        ),
        value_fn=lambda appliance: appliance.get_current_hood_auto_switch_off_event(),
    ),
)


def build_entities_for_appliance(
    appliance_data, coordinators
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities = []

    if isinstance(appliance_data, HDAppliance):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in HOOD_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set binary sensor for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class ElectroluxSensor(ElectroluxBaseEntity[HDAppliance], BinarySensorEntity):
    """Representation of a generic binary sensor for Electrolux appliances."""

    def __init__(
        self,
        appliance_data: HDAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(appliance_data, coordinator)
        self.entity_description = description
        self._attr_name = getattr(description, "name", None)
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.key}"
        )
        self._value_fn = description.value_fn
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_is_on = self._get_value()

    def _get_value(self) -> Any:
        return self._value_fn(self._appliance_data)
