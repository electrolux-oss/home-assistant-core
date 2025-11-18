"""Select entity for Electrolux Group Integration."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any

from electrolux_group_developer_sdk.client.appliances.appliance_data import (
    ApplianceData,
)
from electrolux_group_developer_sdk.client.appliances.dw_appliance import DWAppliance
from electrolux_group_developer_sdk.client.appliances.hb_appliance import HBAppliance
from electrolux_group_developer_sdk.client.appliances.hd_appliance import HDAppliance
from electrolux_group_developer_sdk.client.appliances.ov_appliance import OVAppliance
from electrolux_group_developer_sdk.client.appliances.so_appliance import SOAppliance
from electrolux_group_developer_sdk.client.appliances.td_appliance import TDAppliance
from electrolux_group_developer_sdk.client.appliances.wd_appliance import WDAppliance
from electrolux_group_developer_sdk.client.appliances.wm_appliance import WMAppliance
from electrolux_group_developer_sdk.constants import (
    APPLIANCE_STATE_IDLE,
    APPLIANCE_STATE_READY_TO_START,
    APPLIANCE_STATE_RUNNING,
    RC_ENABLED,
    RC_NOT_SAFETY_RELEVANT_ENABLED,
)
from electrolux_group_developer_sdk.feature_constants import (
    HOOD_FAN_LEVEL,
    HOOD_FAN_SPEED,
    HOOD_STATE,
    KEY_SOUND_TONE,
    PROGRAM,
    PROGRAM_CAPABILITY,
    SPIN_SPEED_CAPABILITY,
    TEMPERATURE_CAPABILITY,
)

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper

_LOGGER = logging.getLogger(__name__)
# Track runtime data per-appliance
_runtime_additional_data: dict[str, dict[str, str]] = {}
LAST_SELECTED_PROGRAM_KEY = "last_selected_program"


@dataclass(frozen=True)
class ElectroluxSelectDescription(SelectEntityDescription):
    """Custom select description for Electrolux select."""

    name: str = ""
    unique_id_suffix: str = ""
    get_current_option: Callable[[Any], Any] = lambda x: None
    get_supported_options: Callable[[Any], Any] = lambda x: None
    is_available_fn: Callable[[Any], Any] = lambda x: None
    set_option_fn: Callable[[Any, str, Any], Awaitable[None]] = (
        lambda _a, _b, _c: asyncio.sleep(0)
    )
    is_supported_fn: Callable[..., Any] = lambda *args: None


async def set_temperature_option(entity, option: str, appliance_data) -> None:
    """Send care temperature command."""

    program = _runtime_additional_data.get(entity.appliance_id, {}).get(
        LAST_SELECTED_PROGRAM_KEY
    )
    await entity.send_device_command(
        appliance_data.get_set_temperature_command(option, program)
    )


async def set_spin_speed_option(entity, option: str, appliance_data) -> None:
    """Send spin speed command."""
    program = _runtime_additional_data.get(entity.appliance_id, {}).get(
        LAST_SELECTED_PROGRAM_KEY
    )
    await entity.send_device_command(
        appliance_data.get_set_spin_speed_command(option, program)
    )


async def set_care_program_option(entity, option: str, appliance_data) -> None:
    """Send Care program command."""
    if entity.appliance_id not in _runtime_additional_data:
        _runtime_additional_data[entity.appliance_id] = {}
    _runtime_additional_data[entity.appliance_id][LAST_SELECTED_PROGRAM_KEY] = option
    await entity.send_device_command(appliance_data.get_set_program_command(option))


CARE_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription, ...] = (
    ElectroluxSelectDescription(
        key="program",
        name="program",
        unique_id_suffix="program",
        get_current_option=lambda appliance: appliance.get_current_program(),
        get_supported_options=lambda appliance: appliance.get_supported_programs(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state()
            in (APPLIANCE_STATE_READY_TO_START, APPLIANCE_STATE_IDLE)
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        set_option_fn=set_care_program_option,
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            PROGRAM_CAPABILITY
        ),
    ),
    ElectroluxSelectDescription(
        key="temperature",
        name="Temperature",
        unique_id_suffix="temperature",
        get_current_option=lambda appliance: appliance.get_current_temperature(),
        get_supported_options=lambda appliance: appliance.get_supported_temperature(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state() == APPLIANCE_STATE_READY_TO_START
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        set_option_fn=set_temperature_option,
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            TEMPERATURE_CAPABILITY
        ),
    ),
    ElectroluxSelectDescription(
        key="spinSpeed",
        name="Spin speed",
        unique_id_suffix="spinSpeed",
        get_current_option=lambda appliance: appliance.get_current_spin_speeds(),
        get_supported_options=lambda appliance: appliance.get_supported_spin_speeds(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state() == APPLIANCE_STATE_READY_TO_START
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        set_option_fn=set_spin_speed_option,
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            SPIN_SPEED_CAPABILITY
        ),
    ),
)


async def set_ov_program_option(entity, option: str, appliance_data) -> None:
    """Send OV program command."""
    await entity.send_device_command(appliance_data.get_program_command(option))


OV_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription, ...] = (
    ElectroluxSelectDescription(
        key="program",
        name="program",
        unique_id_suffix="program",
        get_current_option=lambda appliance: appliance.get_current_program(),
        get_supported_options=lambda appliance: appliance.get_supported_programs(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state() != APPLIANCE_STATE_RUNNING
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        set_option_fn=set_ov_program_option,
        is_supported_fn=lambda appliance: appliance.is_feature_supported(PROGRAM),
    ),
)


async def set_hb_fan_speed_option(entity, option: str, appliance_data) -> None:
    """Send Hob hood fan speed command."""
    await entity.send_device_command(appliance_data.get_hood_fan_speed_command(option))


async def set_hb_state_option(entity, option: str, appliance_data) -> None:
    """Send Hob hood state command."""
    await entity.send_device_command(appliance_data.get_hood_state_command(option))


async def set_hb_key_sound_tone(entity, option: str, appliance_data) -> None:
    """Send sound tone command."""
    await entity.send_device_command(appliance_data.get_key_sound_tone_command(option))


HB_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription, ...] = (
    ElectroluxSelectDescription(
        key="fanSpeed",
        name="hobHood - Fan speed",
        unique_id_suffix="fanSpeed",
        get_current_option=lambda appliance: appliance.get_current_hood_fan_speed(),
        get_supported_options=lambda appliance: appliance.get_supported_hood_fan_speed(),
        is_available_fn=lambda appliance: appliance.get_current_remote_control()
        in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED),
        set_option_fn=set_hb_fan_speed_option,
        is_supported_fn=lambda appliance: appliance.is_hood_feature_supported(
            HOOD_FAN_SPEED
        ),
    ),
    ElectroluxSelectDescription(
        key="hoodState",
        name="hobHood - State",
        unique_id_suffix="hoodState",
        get_current_option=lambda appliance: appliance.get_current_hood_state(),
        get_supported_options=lambda appliance: appliance.get_supported_hood_state(),
        is_available_fn=lambda appliance: appliance.get_current_remote_control()
        in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED),
        set_option_fn=set_hb_state_option,
        is_supported_fn=lambda appliance: appliance.is_hood_feature_supported(
            HOOD_STATE
        ),
    ),
    ElectroluxSelectDescription(
        key="soundTone",
        name="Sound tone",
        unique_id_suffix="soundTone",
        get_current_option=lambda appliance: appliance.get_current_key_sound_tone(),
        get_supported_options=lambda appliance: appliance.get_supported_key_sound_tone(),
        is_available_fn=lambda appliance: appliance.get_current_remote_control()
        in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED),
        set_option_fn=set_hb_key_sound_tone,
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            KEY_SOUND_TONE
        ),
    ),
)


async def set_hd_fan_level_option(entity, option: str, appliance_data) -> None:
    """Send hood fan level command."""
    await entity.send_device_command(
        appliance_data.get_set_hood_fan_level_command(option)
    )


HD_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription, ...] = (
    ElectroluxSelectDescription(
        key="fanLevel",
        name="Fan level",
        unique_id_suffix="fanLevel",
        get_current_option=lambda appliance: appliance.get_current_hood_fan_level(),
        get_supported_options=lambda appliance: appliance.get_supported_hood_fan_level(),
        is_available_fn=lambda appliance: appliance.get_current_remote_control()
        in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED),
        set_option_fn=set_hd_fan_level_option,
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            HOOD_FAN_LEVEL
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

    if isinstance(appliance_data, (DWAppliance, TDAppliance, WMAppliance, WDAppliance)):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in CARE_ELECTROLUX_SELECT
            if description.is_supported_fn(appliance_data)
        )

    if isinstance(appliance_data, OVAppliance):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in OV_ELECTROLUX_SELECT
            if description.is_supported_fn(appliance_data)
        )

    if isinstance(appliance_data, HBAppliance):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in HB_ELECTROLUX_SELECT
            if description.is_supported_fn(appliance_data)
        )

    if isinstance(appliance_data, HDAppliance):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in HD_ELECTROLUX_SELECT
            if description.is_supported_fn(appliance_data)
        )

    if isinstance(appliance_data, SOAppliance):
        entities.extend(
            ElectroluxSelectCavityProgramEntity(appliance_data, coordinator, cavity)
            for cavity in appliance_data.get_supported_cavities()
            if appliance_data.is_cavity_feature_supported(cavity, PROGRAM)
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set Select entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class ElectroluxSelectEntity(ElectroluxBaseEntity[ApplianceData], SelectEntity):
    """Generic Electrolux select entity."""

    def __init__(
        self,
        appliance_data: ApplianceData,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxSelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(appliance_data, coordinator)
        self.entity_description: ElectroluxSelectDescription = description
        self._attr_name = description.name
        self._attr_icon = "mdi:format-list-bulleted"
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.unique_id_suffix}"
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        desc = self.entity_description
        self._attr_current_option = desc.get_current_option(self._appliance_data)
        self._attr_options = desc.get_supported_options(self._appliance_data)
        self._attr_available = desc.is_available_fn(self._appliance_data)

    @property
    def available(self) -> bool:
        """True if the selector is available."""
        return self.entity_description.is_available_fn(self._appliance_data)

    async def async_select_option(self, option: str) -> None:
        """Send command to the appliance."""
        await self.entity_description.set_option_fn(self, option, self._appliance_data)


class ElectroluxSelectCavityProgramEntity(
    ElectroluxBaseEntity[SOAppliance], SelectEntity
):
    """Generic Electrolux select cavity program entity."""

    def __init__(
        self,
        appliance_data: SOAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity: str,
    ) -> None:
        """Init select cavity program entity."""
        super().__init__(appliance_data, coordinator)
        self._cavity = cavity
        self._attr_name = f"{cavity} - program"
        self._attr_icon = "mdi:format-list-bulleted"
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_program_{cavity}"
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_current_option = self._appliance_data.get_current_cavity_program(
            self._cavity
        )
        self._attr_options = self._appliance_data.get_cavity_supported_programs(
            self._cavity
        )
        self._attr_available = self._is_available()

    @property
    def available(self) -> bool:
        """True if the selector is available."""
        return self._is_available()

    def _is_available(self) -> bool:
        return (
            self._appliance_data.get_current_cavity_appliance_state(self._cavity)
            != APPLIANCE_STATE_RUNNING
            and self._appliance_data.get_current_remote_control() == RC_ENABLED
        )

    async def async_select_option(self, option: str) -> None:
        """Send command to the appliance."""
        command = self._appliance_data.get_program_command(self._cavity, option)
        await self.send_device_command(command)
