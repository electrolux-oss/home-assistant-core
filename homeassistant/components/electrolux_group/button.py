"""Button entity for Electrolux Group Integration."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, cast

from electrolux_group_developer_sdk.client.appliances.dw_appliance import DWAppliance
from electrolux_group_developer_sdk.client.appliances.ov_appliance import OVAppliance
from electrolux_group_developer_sdk.client.appliances.so_appliance import SOAppliance
from electrolux_group_developer_sdk.client.appliances.td_appliance import TDAppliance
from electrolux_group_developer_sdk.client.appliances.wd_appliance import WDAppliance
from electrolux_group_developer_sdk.client.appliances.wm_appliance import WMAppliance
from electrolux_group_developer_sdk.constants import (
    APPLIANCE_STATE_DELAYED_START,
    APPLIANCE_STATE_END_OF_CYCLE,
    APPLIANCE_STATE_IDLE,
    APPLIANCE_STATE_OFF,
    APPLIANCE_STATE_PAUSED,
    APPLIANCE_STATE_READY_TO_START,
    APPLIANCE_STATE_RUNNING,
)
from electrolux_group_developer_sdk.feature_constants import EXECUTE_COMMAND

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import ApplianceData
from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ElectroluxButtonEntityDescription(ButtonEntityDescription):
    """Custom button entity description for Electrolux buttons."""

    is_supported_fn: Callable[..., Any] = lambda *args: None


ELECTROLUX_CARE_BUTTONS: tuple[ElectroluxButtonEntityDescription, ...] = (
    ElectroluxButtonEntityDescription(
        key="start",
        name="Appliance Start",
        icon="mdi:play",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            EXECUTE_COMMAND
        ),
    ),
    ElectroluxButtonEntityDescription(
        key="pause",
        name="Appliance Pause",
        icon="mdi:pause",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            EXECUTE_COMMAND
        ),
    ),
    ElectroluxButtonEntityDescription(
        key="stop",
        name="Appliance Stop",
        icon="mdi:stop",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            EXECUTE_COMMAND
        ),
    ),
    ElectroluxButtonEntityDescription(
        key="resume",
        name="Appliance Resume",
        icon="mdi:play-circle",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            EXECUTE_COMMAND
        ),
    ),
)

ELECTROLUX_OVEN_BUTTONS: tuple[ElectroluxButtonEntityDescription, ...] = (
    ElectroluxButtonEntityDescription(
        key="start",
        name="Start",
        icon="mdi:play",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            EXECUTE_COMMAND
        ),
    ),
    ElectroluxButtonEntityDescription(
        key="stop",
        name="Stop",
        icon="mdi:stop",
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            EXECUTE_COMMAND
        ),
    ),
)

ELECTROLUX_SO_OVEN_BUTTONS: tuple[ElectroluxButtonEntityDescription, ...] = (
    ElectroluxButtonEntityDescription(
        key="start",
        name="Start",
        icon="mdi:play",
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, EXECUTE_COMMAND
        ),
    ),
    ElectroluxButtonEntityDescription(
        key="stop",
        name="Stop",
        icon="mdi:stop",
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, EXECUTE_COMMAND
        ),
    ),
)


def build_entities_for_appliance(
    appliance_data, coordinators
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities: list[ElectroluxBaseEntity] = []

    if isinstance(appliance_data, (WMAppliance, WDAppliance, TDAppliance, DWAppliance)):
        entities.extend(
            ElectroluxCareButtonEntity(appliance_data, coordinator, description)
            for description in ELECTROLUX_CARE_BUTTONS
            if description.is_supported_fn(appliance_data)
        )

    if isinstance(appliance_data, OVAppliance):
        entities.extend(
            ElectroluxOvenButtonEntity(appliance_data, coordinator, description)
            for description in ELECTROLUX_OVEN_BUTTONS
            if description.is_supported_fn(appliance_data)
        )

    if isinstance(appliance_data, SOAppliance):
        entities.extend(
            ElectroluxOvenCavityButtonEntity(
                appliance_data, coordinator, description, cavity
            )
            for description in ELECTROLUX_SO_OVEN_BUTTONS
            for cavity in appliance_data.get_supported_cavities()
            if description.is_supported_fn(appliance_data, cavity)
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set button entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class ElectroluxCareButtonEntity(ElectroluxBaseEntity[ApplianceData], ButtonEntity):
    """Unified Electrolux care button entity."""

    def __init__(
        self,
        appliance_data: ApplianceData,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxButtonEntityDescription,
    ) -> None:
        """Init button entity for Electrolux Integration."""
        super().__init__(appliance_data, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.key}"
        )
        self._appliance = cast(
            WMAppliance | WDAppliance | TDAppliance | DWAppliance,
            self._appliance_data,
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_available = self._is_button_available()

    @property
    def available(self) -> bool:
        "True if the button can be pressed."
        return self._is_button_available()

    def _is_button_available(self) -> bool:
        "Return true if the button can be pressed."

        if self._appliance.get_current_remote_control() != "ENABLED":
            return False
        state = self._appliance.get_current_appliance_state()
        key = self.entity_description.key

        if key == "start":
            return state in (APPLIANCE_STATE_READY_TO_START, APPLIANCE_STATE_IDLE)
        if key == "pause":
            return state in (APPLIANCE_STATE_RUNNING, APPLIANCE_STATE_DELAYED_START)
        if key in ("stop", "resume"):
            return state == APPLIANCE_STATE_PAUSED
        return False

    async def async_press(self) -> None:
        """Handle the button press."""
        key = self.entity_description.key

        if key == "start":
            command = self._appliance.get_start_command()
        elif key == "pause":
            command = self._appliance.get_pause_command()
        elif key == "stop":
            command = self._appliance.get_stop_command()
        elif key == "resume":
            command = self._appliance.get_resume_command()
        else:
            _LOGGER.warning("Unknown button action: %s", key)
            return

        await self.send_device_command(command)


class ElectroluxOvenButtonEntity(ElectroluxBaseEntity[OVAppliance], ButtonEntity):
    """Unified Electrolux oven button entity."""

    def __init__(
        self,
        appliance_data: OVAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxButtonEntityDescription,
    ) -> None:
        """Init button entity for Electrolux Integration."""
        super().__init__(appliance_data, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.key}"
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_available = self._is_button_available()

    @property
    def available(self) -> bool:
        "True if the button can be pressed."
        return self._is_button_available()

    def _is_button_available(self) -> bool:
        "Return true if the button can be pressed."
        if self._appliance_data.get_current_remote_control() != "ENABLED":
            return False
        state = self._appliance_data.get_current_appliance_state()
        key = self.entity_description.key

        if key == "start":
            return state in (
                APPLIANCE_STATE_READY_TO_START,
                APPLIANCE_STATE_IDLE,
                APPLIANCE_STATE_OFF,
                APPLIANCE_STATE_PAUSED,
            )
        if key == "stop":
            return state in (
                APPLIANCE_STATE_PAUSED,
                APPLIANCE_STATE_RUNNING,
                APPLIANCE_STATE_END_OF_CYCLE,
                APPLIANCE_STATE_DELAYED_START,
            )
        return False

    async def async_press(self) -> None:
        """Handle the button press."""
        key = self.entity_description.key

        if key == "start":
            command = self._appliance_data.get_start_command()
        elif key == "stop":
            command = self._appliance_data.get_stop_command()
        else:
            _LOGGER.warning("Unknown button action: %s", key)
            return

        await self.send_device_command(command)


class ElectroluxOvenCavityButtonEntity(ElectroluxBaseEntity[SOAppliance], ButtonEntity):
    """Unified Electrolux oven cavity button entity."""

    def __init__(
        self,
        appliance_data: SOAppliance,
        coordinator,
        description: ElectroluxButtonEntityDescription,
        cavity,
    ) -> None:
        """Init button entity for Electrolux Integration."""
        super().__init__(appliance_data, coordinator)
        self.entity_description = description
        self._cavity = cavity
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.key}_{cavity}"
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_available = self._is_button_available()

    @property
    def available(self) -> bool:
        """Return true if the button can be pressed."""
        return self._is_button_available()

    def _is_button_available(self) -> bool:
        """Return true if the button can be pressed."""
        if self._appliance_data.get_current_remote_control() != "ENABLED":
            return False
        state = self._appliance_data.get_current_cavity_appliance_state(self._cavity)
        key = self.entity_description.key

        if key == "start":
            return state in (
                APPLIANCE_STATE_READY_TO_START,
                APPLIANCE_STATE_IDLE,
                APPLIANCE_STATE_OFF,
                APPLIANCE_STATE_PAUSED,
            )
        if key == "stop":
            return state in (
                APPLIANCE_STATE_PAUSED,
                APPLIANCE_STATE_RUNNING,
                APPLIANCE_STATE_END_OF_CYCLE,
                APPLIANCE_STATE_DELAYED_START,
            )
        return False

    async def async_press(self) -> None:
        """Handle the button press."""
        key = self.entity_description.key

        if key == "start":
            command = self._appliance_data.get_start_command(self._cavity)
        elif key == "stop":
            command = self._appliance_data.get_stop_command(self._cavity)
        else:
            _LOGGER.warning("Unknown button action: %s", key)
            return

        await self.send_device_command(command)
