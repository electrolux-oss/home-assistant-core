"""Select entity for Electrolux Integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxConfigEntry, ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper
from .util import convert_to_snake_case


@dataclass(frozen=True, kw_only=True)
class ElectroluxSelectDescription[T: ApplianceData](SelectEntityDescription):
    """Custom select description for Electrolux select."""

    command_mapper_fn: Callable[[str, T], dict[str, Any]]
    exists_fn: Callable[[T], bool] = lambda appliance: True
    get_current_option: Callable[[T], Any] = lambda appliance: None
    get_supported_options: Callable[[T], Any] = lambda appliance: None
    is_available_fn: Callable[[T], bool]


@dataclass(frozen=True, kw_only=True)
class ElectroluxSubmoduleSelectDescription[T: ApplianceData](SelectEntityDescription):
    """Custom select description for Electrolux select."""

    command_mapper_fn: Callable[[str, T, str], dict[str, Any]]
    exists_fn: Callable[[T, str], Any] = lambda appliance, submodule: None
    get_current_option: Callable[[T, str], Any] = lambda appliance, submodule: None
    get_supported_options: Callable[[T, str], Any] = lambda appliance, submodule: None
    is_available_fn: Callable[[T, str], Any] = lambda appliance, submodule: None


def set_temperature_option(
    option: str, appliance_data: WDAppliance | WMAppliance
) -> dict[str, Any]:
    """Send care temperature command."""

    current_program = appliance_data.get_current_program()
    return appliance_data.get_set_temperature_command(option, current_program)


def set_spin_speed_option(
    option: str, appliance_data: WDAppliance | WMAppliance
) -> dict[str, Any]:
    """Send spin speed command."""

    current_program = appliance_data.get_current_program()
    return appliance_data.get_set_spin_speed_command(option, current_program)


def set_care_program_option(
    option: str, appliance_data: DWAppliance | WDAppliance | WMAppliance | TDAppliance
) -> dict[str, Any]:
    """Send Care program command."""

    return appliance_data.get_set_program_command(option)


CARE_ELECTROLUX_SELECT: tuple[
    ElectroluxSelectDescription[DWAppliance | WDAppliance | WMAppliance | TDAppliance],
    ...,
] = (
    ElectroluxSelectDescription(
        key="program",
        translation_key="program",
        get_current_option=lambda appliance: appliance.get_current_program(),
        get_supported_options=lambda appliance: appliance.get_supported_programs(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state()
            in (APPLIANCE_STATE_READY_TO_START, APPLIANCE_STATE_IDLE)
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        command_mapper_fn=set_care_program_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(PROGRAM_CAPABILITY),
    ),
)


WM_WD_ELECTROLUX_SELECT: tuple[
    ElectroluxSelectDescription[WDAppliance | WMAppliance], ...
] = (
    ElectroluxSelectDescription(
        key="temperature",
        translation_key="temperature",
        get_current_option=lambda appliance: appliance.get_current_temperature(),
        get_supported_options=lambda appliance: appliance.get_supported_temperature(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state() == APPLIANCE_STATE_READY_TO_START
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        command_mapper_fn=set_temperature_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(
            TEMPERATURE_CAPABILITY
        ),
    ),
    ElectroluxSelectDescription(
        key="spin_speed",
        translation_key="spin_speed",
        get_current_option=lambda appliance: appliance.get_current_spin_speeds(),
        get_supported_options=lambda appliance: appliance.get_supported_spin_speeds(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state() == APPLIANCE_STATE_READY_TO_START
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        command_mapper_fn=set_spin_speed_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(
            SPIN_SPEED_CAPABILITY
        ),
    ),
)


def set_hb_fan_speed_option(option: str, appliance_data) -> dict[str, Any]:
    """Send Hob hood fan speed command."""
    return appliance_data.get_hood_fan_speed_command(option)


def set_hb_state_option(option: str, appliance_data) -> dict[str, Any]:
    """Send Hob hood state command."""
    return appliance_data.get_hood_state_command(option)


def set_hb_key_sound_tone(option: str, appliance_data) -> dict[str, Any]:
    """Send sound tone command."""
    return appliance_data.get_key_sound_tone_command(option)


HB_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription[HBAppliance], ...] = (
    ElectroluxSelectDescription(
        key="hood_fan_speed",
        translation_key="hood_fan_speed",
        get_current_option=lambda appliance: appliance.get_current_hood_fan_speed(),
        get_supported_options=lambda appliance: (
            appliance.get_supported_hood_fan_speed()
        ),
        is_available_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hb_fan_speed_option,
        exists_fn=lambda appliance: appliance.is_hood_feature_supported(HOOD_FAN_SPEED),
    ),
    ElectroluxSelectDescription(
        key="hood_state",
        translation_key="hood_state",
        get_current_option=lambda appliance: appliance.get_current_hood_state(),
        get_supported_options=lambda appliance: appliance.get_supported_hood_state(),
        is_available_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hb_state_option,
        exists_fn=lambda appliance: appliance.is_hood_feature_supported(HOOD_STATE),
    ),
    ElectroluxSelectDescription(
        key="sound_tone",
        translation_key="sound_tone",
        get_current_option=lambda appliance: appliance.get_current_key_sound_tone(),
        get_supported_options=lambda appliance: (
            appliance.get_supported_key_sound_tone()
        ),
        is_available_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hb_key_sound_tone,
        exists_fn=lambda appliance: appliance.is_feature_supported(KEY_SOUND_TONE),
    ),
)


def set_hd_fan_level_option(option: str, appliance_data) -> dict[str, Any]:
    """Send hood fan level command."""
    return appliance_data.get_set_hood_fan_level_command(option)


HD_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription[HDAppliance], ...] = (
    ElectroluxSelectDescription(
        key="fan_level",
        translation_key="fan_level",
        get_current_option=lambda appliance: appliance.get_current_hood_fan_level(),
        get_supported_options=lambda appliance: (
            appliance.get_supported_hood_fan_level()
        ),
        is_available_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hd_fan_level_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(HOOD_FAN_LEVEL),
    ),
)


def set_ov_program_option(option: str, appliance_data: OVAppliance) -> dict[str, Any]:
    """Send OV program command."""
    return appliance_data.get_program_command(option)


OV_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription[OVAppliance], ...] = (
    ElectroluxSelectDescription(
        key="program",
        translation_key="program",
        get_current_option=lambda appliance: appliance.get_current_program(),
        get_supported_options=lambda appliance: appliance.get_supported_programs(),
        is_available_fn=lambda appliance: (
            appliance.get_current_appliance_state() != APPLIANCE_STATE_RUNNING
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        command_mapper_fn=set_ov_program_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(PROGRAM),
    ),
)


def set_so_program_option(
    option: str, appliance_data: SOAppliance, cavity: str
) -> dict[str, Any]:
    """Send SO program command."""
    return appliance_data.get_program_command(cavity, option)


SO_ELECTROLUX_SELECT: tuple[ElectroluxSubmoduleSelectDescription[SOAppliance], ...] = (
    ElectroluxSubmoduleSelectDescription[SOAppliance](
        key="program",
        translation_key="program",
        get_current_option=lambda appliance, submodule: (
            appliance.get_current_cavity_program(submodule)
        ),
        get_supported_options=lambda appliance, submodule: (
            appliance.get_cavity_supported_programs(submodule)
        ),
        is_available_fn=lambda appliance, submodule: (
            appliance.get_current_cavity_appliance_state(submodule)
            != APPLIANCE_STATE_RUNNING
            and appliance.get_current_remote_control() == RC_ENABLED
        ),
        command_mapper_fn=set_so_program_option,
        exists_fn=lambda appliance, submodule: appliance.is_feature_supported(PROGRAM),
    ),
)


def build_entities_for_appliance(
    appliance_data: ApplianceData,
    coordinators: dict[str, ElectroluxDataUpdateCoordinator],
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities: list[ElectroluxBaseEntity] = []

    if isinstance(appliance_data, (DWAppliance, TDAppliance, WMAppliance, WDAppliance)):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in CARE_ELECTROLUX_SELECT
            if description.exists_fn(appliance_data)
        )

    if isinstance(appliance_data, HBAppliance):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in HB_ELECTROLUX_SELECT
            if description.exists_fn(appliance_data)
        )

    if isinstance(appliance_data, HDAppliance):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in HD_ELECTROLUX_SELECT
            if description.exists_fn(appliance_data)
        )

    if isinstance(appliance_data, OVAppliance):
        entities.extend(
            ElectroluxSelectEntity(appliance_data, coordinator, description)
            for description in OV_ELECTROLUX_SELECT
            if description.exists_fn(appliance_data)
        )

    if isinstance(appliance_data, SOAppliance):
        entities.extend(
            ElectroluxSelectCavityProgramEntity(
                appliance_data, coordinator, description, cavity
            )
            for cavity in appliance_data.get_supported_cavities()
            for description in SO_ELECTROLUX_SELECT
            if appliance_data.is_cavity_feature_supported(cavity, PROGRAM)
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectroluxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set Select entity for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class ElectroluxSelectEntity[T: ApplianceData](ElectroluxBaseEntity[T], SelectEntity):
    """Generic Electrolux select entity."""

    entity_description: ElectroluxSelectDescription[T]

    def __init__(
        self,
        appliance_data: T,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxSelectDescription[T],
    ) -> None:
        """Initialize the select entity."""
        super().__init__(appliance_data, coordinator, description.key)
        self.entity_description = description
        self._attr_options = description.get_supported_options(self._appliance_data)

    @override
    def _update_attr_state(self) -> bool:
        state_changed = False

        new_option = self.entity_description.get_current_option(self._appliance_data)
        if self._attr_current_option != new_option:
            self._attr_current_option = new_option
            state_changed = True

        new_available = self.entity_description.is_available_fn(self._appliance_data)
        if self._attr_available != new_available:
            self._attr_available = new_available
            state_changed = True
        return state_changed

    @property
    @override
    def available(self) -> bool:
        """Return true if the selector is available."""
        return self.entity_description.is_available_fn(self._appliance_data)

    @override
    async def async_select_option(self, option: str) -> None:
        """Send command to the appliance."""
        command = self.entity_description.command_mapper_fn(
            option, self._appliance_data
        )
        await self.coordinator.client.send_command(self._appliance_id, command)
        await self.coordinator.async_refresh()


class ElectroluxSelectCavityProgramEntity[T: ApplianceData](
    ElectroluxBaseEntity[T], SelectEntity
):
    """Generic Electrolux select cavity program entity."""

    entity_description: ElectroluxSubmoduleSelectDescription[T]

    def __init__(
        self,
        appliance_data: T,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxSubmoduleSelectDescription[T],
        cavity: str,
    ) -> None:
        """Init select cavity program entity."""
        entity_key = f"{convert_to_snake_case(cavity)}_{description.key}"
        translation_key = (
            f"{convert_to_snake_case(cavity)}_{description.translation_key}"
        )
        super().__init__(appliance_data, coordinator, entity_key)

        self._cavity = cavity
        self._attr_translation_key = translation_key
        self.entity_description = description
        self._attr_options = self.entity_description.get_supported_options(
            self._appliance_data, self._cavity
        )

    @override
    def _update_attr_state(self) -> bool:
        state_changed = False

        new_option = self.entity_description.get_current_option(
            self._appliance_data, self._cavity
        )
        if self._attr_current_option != new_option:
            self._attr_current_option = new_option
            state_changed = True

        new_available = self.entity_description.is_available_fn(
            self._appliance_data, self._cavity
        )
        if self._attr_available != new_available:
            self._attr_available = new_available
            state_changed = True
        return state_changed

    @property
    @override
    def available(self) -> bool:
        """Return true if the selector is available."""
        return self._is_available()

    def _is_available(self) -> bool:
        return self.entity_description.is_available_fn(
            self._appliance_data, self._cavity
        )

    @override
    async def async_select_option(self, option: str) -> None:
        """Send command to the appliance."""
        command = self.entity_description.command_mapper_fn(
            option, self._appliance_data, self._cavity
        )
        await self.coordinator.client.send_command(self._appliance_id, command)
        await self.coordinator.async_refresh()
