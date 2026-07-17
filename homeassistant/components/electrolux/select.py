"""Select entity for Electrolux Integration."""

from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Concatenate, override

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
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import ElectroluxConfigEntry, ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper
from .util import convert_to_snake_case

OVEN_PROGRAM_TO_HA_PROGRAM: dict[str, str] = {
    "AUGRATIN": "augratin",
    "BOTTOM": "bottom",
    "BREAD_BAKING": "bread_baking",
    "CONVENTIONAL_COOKING": "conventional_cooking",
    "BOTTOM_GRILL": "conventional_cooking",
    "DEFROST": "defrost",
    "DEHYDRATE": "dehydrate",
    "DIRECT_STEAM": "steam_bake",
    "STEAM_DIRECT": "steam_bake",
    "DOUGH_PROVING": "dough_proofing",
    "DRYING": "dehydrate",
    "FROZEN_FOOD": "frozen_foods",
    "BOTTOM_GRILL_FAN": "frozen_foods",
    "FULL_STEAM": "full_steam",
    "GRILL": "grill",
    "GRILL_FAN": "turbo_grill",
    "HUMIDITY_HIGH": "steam_high",
    "HUMIDITY_LOW": "steam_low",
    "HUMIDITY_MEDIUM": "steam_medium",
    "KEEP_WARM": "keep_warm",
    "LOW_STEAM": "steam_low",
    "MOIST_FAN_BAKING": "moist_fan_bake",
    "MOIST_FAN_BAKE": "moist_fan_bake",
    "PASTA_STEAMED": "pasta",
    "PIZZA": "pizza",
    "PIZZA_FROZEN": "pizza_frozen",
    "PIZZA_WARM_UP": "pizza_warm_up",
    "STONE_BAKED_PIZZA": "pizza_stone_baked",
    "CAULIFLOWER_PIZZA": "pizza_cauliflower",
    "GLUTENFREE_PIZZA": "pizza_glutenfree",
    "CALZONE": "calzone",
    "NA_PITA": "pita_bread",
    "NA_NAAN": "naan",
    "NA_MATZAH": "matzah",
    "SLOW_COOKER": "slow_cooking",
    "BOTTOM_TRUE_FAN": "pizza",
    "PLATE_WARMING": "plate_warming",
    "PRESERVING": "preserving",
    "REGENERATE": "steam_regenerating",
    "SOUS_VIDE": "sous_vide",
    "STEAM_REGENERATING": "steam_regenerating",
    "TRUE_FAN": "true_fan",
    "TURBO_GRILL": "turbo_grill",
    "YOGHURT": "yoghurt",
    "STEAM_FRY": "steamify",
    "STEAMIFY": "steamify",
    "CLEAN_DESCALING": "descaling",
    "CLEAN_DRYING": "drying",
    "STEAM_CLEAN_DRY": "drying",
    "STEAM_SYSTEM_CLEAN_DRY": "drying",
    "STEAM_CLEAN_DESCALE": "descaling",
    "STEAM_CLEAN_INTENSE": "steam_clean_plus",
    "STEAM_CLEAN_LIGHT": "steam_clean",
    "STEAM_CLEAN_RINSING": "rinsing",
    "STEAM_CLEAN_RINSE": "rinsing",
    "STEAM_SYSTEM_CLEAN_RINSE": "rinsing",
    "STEAM_CLEAN_TANK_EMPTY": "tank_empty",
    "STEAM_SYSTEM_CLEAN_TANK_EMPTY": "tank_empty",
    "PYRO_CLEAN_LIGHT": "pyro_clean_quick",
    "PYRO_CLEAN_NORMAL": "pyro_clean_normal",
    "PYRO_CLEAN_INTENSE": "pyro_clean_intense",
    "AIR_FRY": "air_fry",
    "BAKE": "bake",
    "BAKE_BROIL": "top_bottom",
    "BAKE_BROIL_FAN": "hot_air_top_bottom",
    "BAKE_TRUE_FAN": "hot_air_bottom",
    "BAKE_TRUE_FAN_STEAM": "hot_air_bottom_steam",
    "BREAD_PROOF": "dough_proofing",
    "CONVENTIONAL_BAKE": "conventional_bake",
    "CONVENTIONAL_ROAST": "conventional_roast",
    "PRE_HEAT": "no_preheat",
    "MULTI_RACK_COOKING": "multi_rack",
    "TURKEY": "turkey",
    "BROIL": "broil",
    "BROIL_FAN": "hot_air_top",
    "STEAM_ROAST": "steam_roast",
    "STEAM_BAKE": "steam_bake",
    "DIRECT_STEAM_STEAM_BAKE": "steam_bake",
    "STEAM_CLEAN": "steam_clean",
    "SELF_CLEAN": "self_clean",
    "SLOW_COOKING": "slow_cooking",
    "DOUGH_PROOFING": "dough_proofing",
    "MEAT_AND_FISH_STEAMED": "meat_and_fish",
    "PASTA_AND_PIZZA_STEAMED": "pasta_and_pizza",
    "BREAD_STEAMED": "bread_baking",
    "PIES_AND_CAKES_STEAMED": "pies",
    "VEGETABLES_STEAMED": "vegetables",
    "POTATO_NATURA_AIRFRY": "rustic_potatoes",
    "NUGGETS_AIRFRY": "nuggets_and_chicken_wings",
    "CHEESE_BREAD_AIRFRY": "cheese_bread",
    "FROZEN_FRENCH_FRIES_AIRFRY": "frozen_french_fries",
    "CHIPS_AIRFRY": "chips",
    "AIR_SOUS_VIDE": "air_sous_vide",
    "WATER_BATH": "water_bath",
    "ASSIST_DIRECT_STEAM_ROAST_BEEF_RARE": "steam_meat",
    "STEAM_MEAT": "steam_meat",
    "MANUAL_AIRFRY": "manual",
    "MICROWAVE_BAKE_BROIL": "microwave_conventional_cooking",
    "MICROWAVE_BROIL": "microwave_grill",
    "MICROWAVE_GRILL": "microwave_grill",
    "MICROWAVE_BROIL_FAN": "microwave_turbo_grill",
    "MICROWAVE_PURE_FULL": "microwave",
    "MICROWAVE_TRUE_FAN": "microwave_true_fan",
    "DIRECT_STEAM_BREAD_BAKING": "bread_baking",
    "DIRECT_STEAM_REGENERATE": "steam_regenerating",
    "CATA_CLEAN_NORMAL": "catalytic_cleaning",
    "STEAM_LOW": "steam_low",
    "STEAM_MEDIUM": "steam_medium",
    "STEAM_HIGH": "steam_high",
    "TWO_TIMER_PROGRAM_SOUS_VIDE_NORMAL": "precision_steam",
    "PRO_STEAM": "pro_steam",
}


@dataclass(frozen=True, kw_only=True)
class ElectroluxSelectBaseDescription[T: ApplianceData, **P = []](
    SelectEntityDescription
):
    """Custom select description for Electrolux select."""

    command_mapper_fn: Callable[Concatenate[str, T, P], dict[str, Any]]
    exists_fn: Callable[Concatenate[T, P], bool]
    get_current_option: Callable[Concatenate[T, P], str]
    get_supported_options: Callable[Concatenate[T, P], list[str]]
    remote_control_check_fn: Callable[Concatenate[T, P], bool]
    available_fn: Callable[Concatenate[T, P], bool]
    electrolux_ha_map: dict[str, str]


@dataclass(frozen=True, kw_only=True)
class ElectroluxSelectDescription[T: ApplianceData](
    ElectroluxSelectBaseDescription[T, []]
):
    """Custom select description for Electrolux select."""

    exists_fn: Callable[[T], bool] = lambda appliance: True
    available_fn: Callable[[T], bool] = lambda appliance: True


@dataclass(frozen=True, kw_only=True)
class ElectroluxSubmoduleSelectDescription[T: ApplianceData](
    ElectroluxSelectBaseDescription[T, [str]]
):
    """Custom select description for Electrolux select."""

    exists_fn: Callable[[T, str], bool] = lambda appliance, submodule: True
    available_fn: Callable[[T, str], bool] = lambda appliance, submodule: True


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
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control() == RC_ENABLED
        ),
        available_fn=lambda appliance: (
            appliance.get_current_appliance_state()
            in (APPLIANCE_STATE_READY_TO_START, APPLIANCE_STATE_IDLE)
        ),
        command_mapper_fn=set_care_program_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(PROGRAM_CAPABILITY),
        electrolux_ha_map={},
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
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control() == RC_ENABLED
        ),
        available_fn=lambda appliance: (
            appliance.get_current_appliance_state() == APPLIANCE_STATE_READY_TO_START
        ),
        command_mapper_fn=set_temperature_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(
            TEMPERATURE_CAPABILITY
        ),
        electrolux_ha_map={},
    ),
    ElectroluxSelectDescription(
        key="spin_speed",
        translation_key="spin_speed",
        get_current_option=lambda appliance: appliance.get_current_spin_speeds(),
        get_supported_options=lambda appliance: appliance.get_supported_spin_speeds(),
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control() == RC_ENABLED
        ),
        available_fn=lambda appliance: (
            appliance.get_current_appliance_state() == APPLIANCE_STATE_READY_TO_START
        ),
        command_mapper_fn=set_spin_speed_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(
            SPIN_SPEED_CAPABILITY
        ),
        electrolux_ha_map={},
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
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hb_fan_speed_option,
        exists_fn=lambda appliance: appliance.is_hood_feature_supported(HOOD_FAN_SPEED),
        electrolux_ha_map={},
    ),
    ElectroluxSelectDescription(
        key="hood_state",
        translation_key="hood_state",
        get_current_option=lambda appliance: appliance.get_current_hood_state(),
        get_supported_options=lambda appliance: appliance.get_supported_hood_state(),
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hb_state_option,
        exists_fn=lambda appliance: appliance.is_hood_feature_supported(HOOD_STATE),
        electrolux_ha_map={},
    ),
    ElectroluxSelectDescription(
        key="sound_tone",
        translation_key="sound_tone",
        get_current_option=lambda appliance: appliance.get_current_key_sound_tone(),
        get_supported_options=lambda appliance: (
            appliance.get_supported_key_sound_tone()
        ),
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hb_key_sound_tone,
        exists_fn=lambda appliance: appliance.is_feature_supported(KEY_SOUND_TONE),
        electrolux_ha_map={},
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
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control()
            in (RC_ENABLED, RC_NOT_SAFETY_RELEVANT_ENABLED)
        ),
        command_mapper_fn=set_hd_fan_level_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(HOOD_FAN_LEVEL),
        electrolux_ha_map={},
    ),
)


def set_ov_program_option(option: str, appliance_data: OVAppliance) -> dict[str, Any]:
    """Send OV program command."""
    return appliance_data.get_program_command(option)


OV_ELECTROLUX_SELECT: tuple[ElectroluxSelectDescription[OVAppliance], ...] = (
    ElectroluxSelectDescription(
        key="program",
        translation_key="oven_program",
        get_current_option=lambda appliance: appliance.get_current_program(),
        get_supported_options=lambda appliance: appliance.get_supported_programs(),
        remote_control_check_fn=lambda appliance: (
            appliance.get_current_remote_control() == RC_ENABLED
        ),
        available_fn=lambda appliance: (
            appliance.get_current_appliance_state() != APPLIANCE_STATE_RUNNING
        ),
        command_mapper_fn=set_ov_program_option,
        exists_fn=lambda appliance: appliance.is_feature_supported(PROGRAM),
        electrolux_ha_map=OVEN_PROGRAM_TO_HA_PROGRAM,
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
        translation_key="oven_program",
        get_current_option=lambda appliance, submodule: (
            appliance.get_current_cavity_program(submodule)
        ),
        get_supported_options=lambda appliance, submodule: (
            appliance.get_cavity_supported_programs(submodule)
        ),
        remote_control_check_fn=lambda appliance, submodule: (
            appliance.get_current_remote_control() == RC_ENABLED
        ),
        available_fn=lambda appliance, submodule: (
            appliance.get_current_cavity_appliance_state(submodule)
            != APPLIANCE_STATE_RUNNING
        ),
        command_mapper_fn=set_so_program_option,
        exists_fn=lambda appliance, submodule: appliance.is_cavity_feature_supported(
            submodule, PROGRAM
        ),
        electrolux_ha_map=OVEN_PROGRAM_TO_HA_PROGRAM,
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


class ElectroluxBaseSelect[T: ApplianceData, **P](
    ElectroluxBaseEntity[T], SelectEntity
):
    """Base class for Electrolux select entities."""

    def __init__(
        self,
        appliance_data: T,
        coordinator: ElectroluxDataUpdateCoordinator,
        key: str,
        description: ElectroluxSelectBaseDescription[T, P],
    ) -> None:
        """Initialize the select entity."""
        super().__init__(appliance_data, coordinator, key)

        supported_electrolux_options = self._get_supported_options()
        self._electrolux_ha_map = {
            electrolux_option: ha_option
            for electrolux_option, ha_option in description.electrolux_ha_map.items()
            if electrolux_option in supported_electrolux_options
        }

        self._attr_options = self._get_supported_options()

    @override
    def _update_attr_state(self) -> bool:
        state_changed = False

        new_option = self._get_current_option()
        if self._attr_current_option != new_option:
            self._attr_current_option = new_option
            state_changed = True

        return state_changed

    @abstractmethod
    def _get_supported_options(self) -> list[str]:
        """Return the supported options for the select entity."""

    @abstractmethod
    def _get_current_option(self) -> str | None:
        """Return the current option for the select entity."""

    @abstractmethod
    def _is_remote_control_enabled(self) -> bool:
        """Return True if remote control is enabled for the appliance."""

    @abstractmethod
    def _is_available_state(self) -> bool:
        """Return True if the appliance is in a state where changing the selected option is available."""

    @abstractmethod
    def _get_command(self, option: str) -> dict[str, Any]:
        """Return the command to send to the appliance for the given option."""

    @override
    async def async_select_option(self, option: str) -> None:
        """Send command to the appliance."""
        if not self._is_remote_control_enabled():
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="remote_control_disabled"
            )
        if not self._is_available_state():
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unsupported_state_for_command",
            )

        command = self._get_command(option)
        await self.coordinator.client.send_command(self._appliance_id, command)
        await self.coordinator.async_refresh()


class ElectroluxSelectEntity[T: ApplianceData](ElectroluxBaseSelect[T, []]):
    """Generic Electrolux select entity."""

    entity_description: ElectroluxSelectDescription[T]

    def __init__(
        self,
        appliance_data: T,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxSelectDescription[T],
    ) -> None:
        """Initialize the select entity."""
        self.entity_description = description
        super().__init__(appliance_data, coordinator, description.key, description)

    @override
    def _get_supported_options(self) -> list[str]:
        return self.entity_description.get_supported_options(self._appliance_data)

    @override
    def _get_current_option(self) -> str | None:
        return self.entity_description.get_current_option(self._appliance_data)

    @override
    def _is_remote_control_enabled(self) -> bool:
        return self.entity_description.remote_control_check_fn(self._appliance_data)

    @override
    def _is_available_state(self) -> bool:
        return self.entity_description.available_fn(self._appliance_data)

    @override
    def _get_command(self, option: str) -> dict[str, Any]:
        return self.entity_description.command_mapper_fn(option, self._appliance_data)


class ElectroluxSelectCavityProgramEntity[T: ApplianceData](
    ElectroluxBaseSelect[T, [str]]
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
        self.entity_description = description
        self._cavity = cavity
        entity_key = f"{convert_to_snake_case(cavity)}_{description.key}"
        translation_key = (
            f"{convert_to_snake_case(cavity)}_{description.translation_key}"
        )
        super().__init__(appliance_data, coordinator, entity_key, description)

        self._attr_translation_key = translation_key
        self._attr_options = self.entity_description.get_supported_options(
            self._appliance_data, self._cavity
        )

    @override
    def _get_supported_options(self) -> list[str]:
        return self.entity_description.get_supported_options(
            self._appliance_data, self._cavity
        )

    @override
    def _get_current_option(self) -> str | None:
        return self.entity_description.get_current_option(
            self._appliance_data, self._cavity
        )

    @override
    def _is_remote_control_enabled(self) -> bool:
        return self.entity_description.remote_control_check_fn(
            self._appliance_data, self._cavity
        )

    @override
    def _is_available_state(self) -> bool:
        return self.entity_description.available_fn(self._appliance_data, self._cavity)

    @override
    def _get_command(self, option: str) -> dict[str, Any]:
        return self.entity_description.command_mapper_fn(
            option, self._appliance_data, self._cavity
        )
