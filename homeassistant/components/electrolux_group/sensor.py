"""Sensor entity for Electrolux Group Integration."""

from collections.abc import Callable
import logging
from typing import Any, cast

from electrolux_group_developer_sdk.appliance_config.ap_config import (
    PM_1,
    PM_2_5,
    PM_10,
    TVOC,
)
from electrolux_group_developer_sdk.appliance_config.cr_config import EXTRA_CAVITY
from electrolux_group_developer_sdk.client.appliances.ac_appliance import ACAppliance
from electrolux_group_developer_sdk.client.appliances.ap_appliance import APAppliance
from electrolux_group_developer_sdk.client.appliances.appliance_data import (
    ApplianceData,
)
from electrolux_group_developer_sdk.client.appliances.cr_appliance import CRAppliance
from electrolux_group_developer_sdk.client.appliances.dam_ac_appliance import (
    DAMACAppliance,
)
from electrolux_group_developer_sdk.client.appliances.dh_appliance import DHAppliance
from electrolux_group_developer_sdk.client.appliances.dw_appliance import DWAppliance
from electrolux_group_developer_sdk.client.appliances.hb_appliance import HBAppliance
from electrolux_group_developer_sdk.client.appliances.hd_appliance import HDAppliance
from electrolux_group_developer_sdk.client.appliances.ov_appliance import OVAppliance
from electrolux_group_developer_sdk.client.appliances.rvc_appliance import RVCAppliance
from electrolux_group_developer_sdk.client.appliances.so_appliance import SOAppliance
from electrolux_group_developer_sdk.client.appliances.td_appliance import TDAppliance
from electrolux_group_developer_sdk.client.appliances.wd_appliance import WDAppliance
from electrolux_group_developer_sdk.client.appliances.wm_appliance import WMAppliance
from electrolux_group_developer_sdk.feature_constants import (
    AD_TANK_A_DET_LOADED_CAPABILITY,
    AD_TANK_B_DET_LOADED_CAPABILITY,
    AD_TANK_B_SOFT_LOADED_CAPABILITY,
    AIR_FILTER_STATE,
    ALERTS,
    APPLIANCE_MODE,
    APPLIANCE_STATE,
    BATTERY,
    CYCLE_PHASE,
    DISPLAY_FOOD_PROBE_TEMPERATURE_C,
    DISPLAY_FOOD_PROBE_TEMPERATURE_F,
    DISPLAY_TEMPERATURE_C,
    DISPLAY_TEMPERATURE_F,
    DOOR_STATE,
    ECO_LEVEL_CAPABILITY,
    FOOD_PROBE_STATE,
    HOB_HOOD_TARGET_DURATION,
    HOB_HOOD_WINDOW_NOTIFICATION,
    HOOD_CHARC_FILTER_TIME,
    HOOD_FILTER_CHARC_ENABLE,
    HOOD_GREASE_FILTER_TIMER,
    HUMAN_CENTRIC_LIGHT_EVENT_STATE,
    OPTISENSE_RESULT_CAPABILITY,
    REMOTE_CONTROL,
    RUNNING_TIME,
    SOUND_VOLUME,
    START_TIME,
    STOP_TIME,
    TANK_A_DET_LOAD_FOR_NOMINAL_WEIGHT_CAPABILITY,
    TANK_A_RESERVE_CAPABILITY,
    TANK_B_DET_LOAD_FOR_NOMINAL_WEIGHT_CAPABILITY,
    TANK_B_RESERVE_CAPABILITY,
    TARGET_DURATION,
    TARGET_TEMPERATURE_C,
    TARGET_TEMPERATURE_F,
    TIME_TO_END,
    TVOC_FILTER_TIME,
    UI_LOCK_MODE,
    VACATION_HOLIDAY_MODE,
    WATER_FILTER_STATE,
    WATER_HARDNESS,
    WATER_USAGE_CAPABILITY,
    ZONE_HOB_POT_DETECTED,
    ZONE_REMINDER_TIME,
    ZONE_RESIDUAL_HEAT_STATE,
    ZONE_TARGET_DURATION,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    dataclass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxDataUpdateCoordinator
from .entity import ElectroluxBaseEntity
from .entity_helper import async_setup_entities_helper

_LOGGER = logging.getLogger(__name__)

ELECTROLUX_TO_HA_TEMPERATURE_UNIT = {
    "CELSIUS": UnitOfTemperature.CELSIUS,
    "FAHRENHEIT": UnitOfTemperature.FAHRENHEIT,
}

HOB_ZONE_TO_ICON_MAP = {
    "hobZone1": "mdi:numeric-1-box-outline",
    "hobZone2": "mdi:numeric-2-box-outline",
    "hobZone3": "mdi:numeric-3-box-outline",
    "hobZone4": "mdi:numeric-4-box-outline",
    "hobZone5": "mdi:numeric-5-box-outline",
    "hobZone6": "mdi:numeric-6-box-outline",
    "hobZone7": "mdi:numeric-7-box-outline",
    "hobZone8": "mdi:numeric-8-box-outline",
    "hobZone9": "mdi:numeric-9-box-outline",
}


@dataclass(frozen=True)
class ElectroluxSensorDescription(SensorEntityDescription):
    """Custom sensor description for Electrolux sensors."""

    name: str = ""
    value_fn: Callable[..., Any] = lambda *args: None
    is_supported_fn: Callable[..., Any] = lambda *args: None


GENERAL_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="connection_state",
        name="Connection state",
        icon="mdi:wifi",
        value_fn=lambda appliance: appliance.state.connectionState,
    ),
)

OVEN_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="start_at",
        name="Start at",
        icon="mdi:timer-play-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda appliance: appliance.get_current_start_at(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(START_TIME),
    ),
    ElectroluxSensorDescription(
        key="runnig_time",
        name="Running time",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class="measurement",
        value_fn=lambda appliance: appliance.get_current_running_time(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(RUNNING_TIME),
    ),
    ElectroluxSensorDescription(
        key="appliance_state",
        name="Appliance state",
        icon="mdi:information-outline",
        value_fn=lambda appliance: appliance.get_current_appliance_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            APPLIANCE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="food_probe_state",
        name="Food probe state",
        icon="mdi:thermometer-probe",
        value_fn=lambda appliance: appliance.get_current_food_probe_insertion_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            FOOD_PROBE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="door_state",
        name="Door state",
        icon="mdi:door",
        value_fn=lambda appliance: appliance.get_current_door_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(DOOR_STATE),
    ),
    ElectroluxSensorDescription(
        key="remote_control",
        name="Remote control",
        icon="mdi:remote",
        value_fn=lambda appliance: appliance.get_current_remote_control(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            REMOTE_CONTROL
        ),
    ),
)

OVEN_TEMPERATURE_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="food_probe_temperature",
        name="Food probe temperature",
        icon="mdi:thermometer-probe",
        value_fn=lambda appliance: appliance.get_current_display_food_probe_temperature_f()
        if appliance.get_current_temperature_unit() == "FAHRENHEIT"
        else appliance.get_current_display_food_probe_temperature_c(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            [DISPLAY_FOOD_PROBE_TEMPERATURE_F, DISPLAY_FOOD_PROBE_TEMPERATURE_C]
        ),
    ),
    ElectroluxSensorDescription(
        key="display_temperature",
        name="Current temperature",
        icon="mdi:thermometer",
        value_fn=lambda appliance: appliance.get_current_display_temperature_f()
        if appliance.get_current_temperature_unit() == "FAHRENHEIT"
        else appliance.get_current_display_temperature_c(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            [DISPLAY_TEMPERATURE_C, DISPLAY_TEMPERATURE_F]
        ),
    ),
)

STRUCTURED_OVEN_CAVITY_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="start_at",
        name="Start at",
        icon="mdi:timer-play-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda appliance, cavity: appliance.get_current_cavity_start_at(
            cavity
        ),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, START_TIME
        ),
    ),
    ElectroluxSensorDescription(
        key="runnig_time",
        name="Running time",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class="measurement",
        value_fn=lambda appliance, cavity: appliance.get_current_cavity_running_time(
            cavity
        ),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, RUNNING_TIME
        ),
    ),
    ElectroluxSensorDescription(
        key="appliance_state",
        name="Appliance state",
        icon="mdi:information-outline",
        value_fn=lambda appliance, cavity: appliance.get_current_cavity_appliance_state(
            cavity
        ),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, APPLIANCE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="food_probe_state",
        name="Food probe state",
        icon="mdi:thermometer-probe",
        value_fn=lambda appliance,
        cavity: appliance.get_current_cavity_food_probe_insertion_state(cavity),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, FOOD_PROBE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="door_state",
        name="Door state",
        icon="mdi:door",
        value_fn=lambda appliance, cavity: appliance.get_current_cavity_door_state(
            cavity
        ),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, DOOR_STATE
        ),
    ),
)

STRUCTURED_OVEN_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="remote_control",
        name="Remote control",
        icon="mdi:remote",
        value_fn=lambda appliance: appliance.get_current_remote_control(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            REMOTE_CONTROL
        ),
    ),
)

STRUCTURED_OVEN_CAVITY_TEMPERATURE_ELECTROLUX_SENSORS: tuple[
    ElectroluxSensorDescription, ...
] = (
    ElectroluxSensorDescription(
        key="food_probe_temperature",
        name="Food probe temperature",
        icon="mdi:thermometer-probe",
        value_fn=lambda appliance,
        cavity: appliance.get_current_cavity_display_food_probe_temperature_f(cavity)
        if appliance.get_current_temperature_unit() == "FAHRENHEIT"
        else appliance.get_current_cavity_display_food_probe_temperature_c(cavity),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, [DISPLAY_FOOD_PROBE_TEMPERATURE_C, DISPLAY_FOOD_PROBE_TEMPERATURE_F]
        ),
    ),
    ElectroluxSensorDescription(
        key="display_temperature",
        name="Current temperature",
        icon="mdi:thermometer",
        value_fn=lambda appliance,
        cavity: appliance.get_current_cavity_display_temperature_f(cavity)
        if appliance.get_current_temperature_unit() == "FAHRENHEIT"
        else appliance.get_current_cavity_display_temperature_c(cavity),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, [DISPLAY_TEMPERATURE_C, DISPLAY_TEMPERATURE_F]
        ),
    ),
)


CARE_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="start_at",
        name="Start at",
        icon="mdi:timer-play-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda appliance: appliance.get_current_start_at(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            [STOP_TIME, START_TIME]
        ),
    ),
    ElectroluxSensorDescription(
        key="end_at",
        name="Stop at",
        icon="mdi:timer-stop-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda appliance: appliance.get_current_end_at(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            [STOP_TIME, START_TIME]
        ),
    ),
    ElectroluxSensorDescription(
        key="duration",
        name="Duration",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class="measurement",
        value_fn=lambda appliance: appliance.get_current_time_to_end(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(TIME_TO_END),
    ),
    ElectroluxSensorDescription(
        key="appliance_state",
        name="Appliance state",
        icon="mdi:information-outline",
        value_fn=lambda appliance: appliance.get_current_appliance_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            APPLIANCE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="cycle_phase",
        name="Cycle phase",
        icon="mdi:animation-play",
        value_fn=lambda appliance: appliance.get_current_cycle_phase(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(CYCLE_PHASE),
    ),
    ElectroluxSensorDescription(
        key="door_state",
        name="Door state",
        icon="mdi:door",
        value_fn=lambda appliance: appliance.get_current_door_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(DOOR_STATE),
    ),
    ElectroluxSensorDescription(
        key="remote_control",
        name="Remote control",
        icon="mdi:remote",
        value_fn=lambda appliance: appliance.get_current_remote_control(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            REMOTE_CONTROL
        ),
    ),
    ElectroluxSensorDescription(
        key="water_hardness",
        name="Water hardness",
        icon="mdi:water",
        value_fn=lambda appliance: appliance.get_current_water_hardness(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            WATER_HARDNESS
        ),
    ),
    ElectroluxSensorDescription(
        key="ui_lock_mode",
        name="UI lock mode",
        icon="mdi:lock",
        value_fn=lambda appliance: appliance.get_current_ui_lock_mode(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(UI_LOCK_MODE),
    ),
)

WM_WD_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_water_usage",
        name="fCMiscellaneousState - Water Usage",
        icon="mdi:water",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_water_usage(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            WATER_USAGE_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_ad_tank_b_det_loaded",
        name="fCMiscellaneousState - AD Tank B Detergent Loaded",
        icon="mdi:beaker",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_ad_tank_b_det_loaded(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            AD_TANK_B_DET_LOADED_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_tank_a_det_load_for_nominal_weight",
        name="fCMiscellaneousState - Tank A Detergent Load (Nominal Weight)",
        icon="mdi:scale-balance",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_tank_a_det_load_for_nominal_weight(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            TANK_A_DET_LOAD_FOR_NOMINAL_WEIGHT_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_optisense_result",
        name="fCMiscellaneousState - Optisense Result",
        icon="mdi:eye",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_optisense_result(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            OPTISENSE_RESULT_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_ad_tank_b_soft_loaded",
        name="fCMiscellaneousState - AD Tank B Softener Loaded",
        icon="mdi:beaker-plus",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_ad_tank_b_soft_loaded(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            AD_TANK_B_SOFT_LOADED_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_eco_level",
        name="fCMiscellaneousState - Eco Level",
        icon="mdi:leaf",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_eco_level(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            ECO_LEVEL_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_ad_tank_a_det_loaded",
        name="fCMiscellaneousState - AD Tank A Detergent Loaded",
        icon="mdi:beaker",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_ad_tank_a_det_loaded(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            AD_TANK_A_DET_LOADED_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_tank_b_det_load_for_nominal_weight",
        name="fCMiscellaneousState - Tank B Detergent Load (Nominal Weight)",
        icon="mdi:scale-balance",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_tank_b_det_load_for_nominal_weight(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            TANK_B_DET_LOAD_FOR_NOMINAL_WEIGHT_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_tank_a_reserve",
        name="fCMiscellaneousState - Tank A Reserve",
        icon="mdi:flask-outline",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_tank_a_reserve(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            TANK_A_RESERVE_CAPABILITY
        ),
    ),
    ElectroluxSensorDescription(
        key="f_c_miscellaneous_state_tank_b_reserve",
        name="fCMiscellaneousState - Tank B Reserve",
        icon="mdi:flask-outline",
        value_fn=lambda appliance: appliance.get_current_f_c_miscellaneous_state_tank_b_reserve(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            TANK_B_RESERVE_CAPABILITY
        ),
    ),
)

REFRIGERATOR_GENERIC_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="ui_lock_mode",
        name="UI lock mode",
        icon="mdi:lock",
        value_fn=lambda appliance: appliance.get_current_ui_lock_mode(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(UI_LOCK_MODE),
    ),
    ElectroluxSensorDescription(
        key="water_filter_state",
        name="Water filter state",
        icon="mdi:filter",
        value_fn=lambda appliance: appliance.get_current_water_filter_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            WATER_FILTER_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="air_filter_state",
        name="Air filter state",
        icon="mdi:air-filter",
        value_fn=lambda appliance: appliance.get_current_air_filter_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            AIR_FILTER_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="vacation_mode",
        name="Vacation mode",
        icon="mdi:airplane",
        value_fn=lambda appliance: appliance.get_current_vacation_holiday_mode(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            VACATION_HOLIDAY_MODE
        ),
    ),
)

EXTRA_CAVITY_TEMPERATURE_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="target_temperauture",
        name=f"{EXTRA_CAVITY} - target temperature",
        icon="mdi:thermometer",
        value_fn=lambda appliance: appliance.get_current_cavity_target_temperature_f(
            EXTRA_CAVITY
        )
        if appliance.get_current_temperature_unit() == "FAHRENHEIT"
        else appliance.get_current_cavity_target_temperature_c(EXTRA_CAVITY),
        is_supported_fn=lambda appliance: appliance.is_cavity_feature_supported(
            EXTRA_CAVITY, [TARGET_TEMPERATURE_C, TARGET_TEMPERATURE_F]
        ),
    ),
)

FREEZER_FRIDGE_ICE_MAKER_EXTRA_CAVITY_ELECTROLUX_SENSORS: tuple[
    ElectroluxSensorDescription, ...
] = (
    ElectroluxSensorDescription(
        key="appliance_state",
        name="Appliance state",
        icon="mdi:information-outline",
        value_fn=lambda appliance, cavity: appliance.get_current_cavity_appliance_state(
            cavity
        ),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, APPLIANCE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="door_state",
        name="Door state",
        icon="mdi:door",
        value_fn=lambda appliance, cavity: appliance.get_current_cavity_door_state(
            cavity
        ),
        is_supported_fn=lambda appliance, cavity: appliance.is_cavity_feature_supported(
            cavity, DOOR_STATE
        ),
    ),
)

HOOD_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="hood_charc_filter_timer",
        name="Charcoal filter timer",
        icon="mdi:air-filter",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class="measurement",
        value_fn=lambda appliance: appliance.get_current_hood_charc_filter_timer(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            HOOD_CHARC_FILTER_TIME
        ),
    ),
    ElectroluxSensorDescription(
        key="hood_filter_charc_enable",
        name="Filter charcoal enable",
        icon="mdi:air-filter",
        value_fn=lambda appliance: appliance.get_current_hood_filter_charc_enable(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            HOOD_FILTER_CHARC_ENABLE
        ),
    ),
    ElectroluxSensorDescription(
        key="grease_filter_time",
        name="Grease filter time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class="measurement",
        icon="mdi:air-filter",
        value_fn=lambda appliance: appliance.get_current_hood_grease_filter_time(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            HOOD_GREASE_FILTER_TIMER
        ),
    ),
    ElectroluxSensorDescription(
        key="tvoc_filter_time",
        name="TVOC filter time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class="measurement",
        icon="mdi:air-filter",
        value_fn=lambda appliance: appliance.get_current_tvoc_filter_time(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            TVOC_FILTER_TIME
        ),
    ),
    ElectroluxSensorDescription(
        key="human_centric_light_event_state",
        name="Human centric light event state",
        icon="mdi:ceiling-light-outline",
        value_fn=lambda appliance: appliance.get_current_human_centric_light_event_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            HUMAN_CENTRIC_LIGHT_EVENT_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="appliance_mode",
        name="Appliance mode",
        icon="mdi:tune-variant",
        value_fn=lambda appliance: appliance.get_current_appliance_mode(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            APPLIANCE_MODE
        ),
    ),
    ElectroluxSensorDescription(
        key="appliance_state",
        name="Appliance state",
        icon="mdi:information-outline",
        value_fn=lambda appliance: appliance.get_current_appliance_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            APPLIANCE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="sound_volume",
        name="Sound volume",
        icon="mdi:volume-high",
        value_fn=lambda appliance: appliance.get_current_sound_volume(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(SOUND_VOLUME),
    ),
    ElectroluxSensorDescription(
        key="remote_control",
        name="Remote control",
        icon="mdi:remote",
        value_fn=lambda appliance: appliance.get_current_remote_control(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            REMOTE_CONTROL
        ),
    ),
    ElectroluxSensorDescription(
        key="target_duration",
        name="Target duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class="measurement",
        icon="mdi:timer-outline",
        value_fn=lambda appliance: appliance.get_current_target_duration(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            TARGET_DURATION
        ),
    ),
)

HOB_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="ui_lock_mode",
        name="UI lock mode",
        icon="mdi:lock",
        value_fn=lambda appliance: appliance.get_current_ui_lock_mode(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(UI_LOCK_MODE),
    ),
    ElectroluxSensorDescription(
        key="appliance_mode",
        name="Appliance mode",
        icon="mdi:tune-variant",
        value_fn=lambda appliance: appliance.get_current_appliance_mode(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            APPLIANCE_MODE
        ),
    ),
    ElectroluxSensorDescription(
        key="appliance_state",
        name="Appliance state",
        icon="mdi:information-outline",
        value_fn=lambda appliance: appliance.get_current_appliance_state(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            APPLIANCE_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="remote_control",
        name="Remote control",
        icon="mdi:remote",
        value_fn=lambda appliance: appliance.get_current_remote_control(),
        is_supported_fn=lambda appliance: appliance.is_feature_supported(
            REMOTE_CONTROL
        ),
    ),
    ElectroluxSensorDescription(
        key="hob__hood_windows_notification",
        name="hobHood - Windows notification",
        icon="mdi:window-open-variant",
        value_fn=lambda appliance: appliance.get_current_hob_hood_window_notification(),
        is_supported_fn=lambda appliance: appliance.is_hood_feature_supported(
            HOB_HOOD_WINDOW_NOTIFICATION
        ),
    ),
    ElectroluxSensorDescription(
        key="hob_hood_target_duration",
        name="hobHood - Target duration",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        state_class="measurement",
        value_fn=lambda appliance: appliance.get_current_hob_hood_target_duration(),
        is_supported_fn=lambda appliance: appliance.is_hood_feature_supported(
            HOB_HOOD_TARGET_DURATION
        ),
    ),
)
HOB_ZONE_ELECTROLUX_SENSORS: tuple[ElectroluxSensorDescription, ...] = (
    ElectroluxSensorDescription(
        key="zone_residual_heat_state",
        name="Zone residual heat state",
        value_fn=lambda appliance, hob_zone: (
            appliance.get_current_zone_residual_heat_state(hob_zone)
        ),
        is_supported_fn=lambda appliance,
        hob_zone: appliance.is_hob_zone_feature_supported(
            hob_zone, ZONE_RESIDUAL_HEAT_STATE
        ),
    ),
    ElectroluxSensorDescription(
        key="target_duration",
        name="Target duration",
        value_fn=lambda appliance, hob_zone: appliance.get_current_zone_target_duration(
            hob_zone
        ),
        is_supported_fn=lambda appliance,
        hob_zone: appliance.is_hob_zone_feature_supported(
            hob_zone, ZONE_TARGET_DURATION
        ),
    ),
    ElectroluxSensorDescription(
        key="zone_reminder_time",
        name="Zone reminder time",
        value_fn=lambda appliance, hob_zone: (
            appliance.get_current_zone_residual_heat_state(hob_zone)
        ),
        is_supported_fn=lambda appliance,
        hob_zone: appliance.is_hob_zone_feature_supported(hob_zone, ZONE_REMINDER_TIME),
    ),
    ElectroluxSensorDescription(
        key="zone_hob_pot_detected",
        name="Zone hob pot detected",
        value_fn=lambda appliance, hob_zone: (
            appliance.get_current_zone_hob_pot_detected(hob_zone)
        ),
        is_supported_fn=lambda appliance,
        hob_zone: appliance.is_hob_zone_feature_supported(
            hob_zone, ZONE_HOB_POT_DETECTED
        ),
    ),
)

SENSOR_TYPES: dict[str, Any] = {
    PM_1: {
        "name": "PM1",
        "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "device_class": SensorDeviceClass.PM1,
    },
    PM_2_5: {
        "name": "PM2.5",
        "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "device_class": SensorDeviceClass.PM25,
    },
    PM_10: {
        "name": "PM10",
        "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "device_class": SensorDeviceClass.PM10,
    },
    TVOC: {
        "name": "TVOC",
        "unit": CONCENTRATION_PARTS_PER_BILLION,
        "device_class": None,
    },
}


def build_entities_for_appliance(
    appliance_data, coordinators
) -> list[ElectroluxBaseEntity]:
    """Return all entities for a single appliance."""
    appliance = appliance_data.appliance
    coordinator = coordinators[appliance.applianceId]
    entities: list[ElectroluxBaseEntity] = []

    if isinstance(
        appliance_data,
        (
            APAppliance,
            RVCAppliance,
            WMAppliance,
            WDAppliance,
            TDAppliance,
            DWAppliance,
            OVAppliance,
            HDAppliance,
            HBAppliance,
            CRAppliance,
            DHAppliance,
            ACAppliance,
            SOAppliance,
            DAMACAppliance,
        ),
    ):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in GENERAL_ELECTROLUX_SENSORS
        )

    if isinstance(appliance_data, APAppliance):
        air_quality_mapping = appliance_data.get_air_quality_map() or {}
        if appliance_data.state:
            appliance_state = appliance_data.state.properties.get("reported")

        for air_quality_key, air_quality_property in air_quality_mapping.items():
            if appliance_state and air_quality_property in appliance_state:
                entities.append(
                    AirPurifierAirQualitySensor(
                        appliance_data=appliance_data,
                        coordinator=coordinator,
                        property=air_quality_key,
                    )
                )

    if isinstance(appliance_data, RVCAppliance):
        if appliance_data.is_feature_supported(BATTERY):
            entities.append(
                RVCBatterySensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

    if isinstance(appliance_data, (WMAppliance, WDAppliance, TDAppliance, DWAppliance)):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in CARE_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        if appliance_data.is_feature_supported(ALERTS):
            entities.append(
                ApplianceAlertSensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

    if isinstance(appliance_data, (WMAppliance, WDAppliance)):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in WM_WD_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        if appliance_data.is_feature_supported(ALERTS):
            entities.append(
                ApplianceAlertSensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

    if isinstance(appliance_data, OVAppliance):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in OVEN_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        entities.extend(
            ElectroluxTemperatureSensor(appliance_data, coordinator, description)
            for description in OVEN_TEMPERATURE_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        if appliance_data.is_feature_supported(ALERTS):
            entities.append(
                ApplianceAlertSensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

    if isinstance(appliance_data, SOAppliance):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in STRUCTURED_OVEN_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        entities.extend(
            ElectroluxCavitySensor(appliance_data, coordinator, cavity, description)
            for description in STRUCTURED_OVEN_CAVITY_ELECTROLUX_SENSORS
            for cavity in appliance_data.get_supported_cavities()
            if description.is_supported_fn(appliance_data, cavity)
        )

        entities.extend(
            ElectroluxTemperatureCavitySensor(
                appliance_data, coordinator, cavity, description
            )
            for description in STRUCTURED_OVEN_CAVITY_TEMPERATURE_ELECTROLUX_SENSORS
            for cavity in appliance_data.get_supported_cavities()
            if description.is_supported_fn(appliance_data, cavity)
        )

        if appliance_data.is_feature_supported(ALERTS):
            entities.append(
                ApplianceAlertSensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

    if isinstance(appliance_data, CRAppliance):
        supported_cavities = appliance_data.get_supported_cavities()

        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in REFRIGERATOR_GENERIC_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        entities.extend(
            ElectroluxCavitySensor(appliance_data, coordinator, cavity, description)
            for cavity in supported_cavities
            for description in FREEZER_FRIDGE_ICE_MAKER_EXTRA_CAVITY_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data, cavity)
        )

        entities.extend(
            ElectroluxTemperatureSensor(appliance_data, coordinator, description)
            for description in EXTRA_CAVITY_TEMPERATURE_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        entities.extend(
            ApplianceAlertCavitySensor(appliance_data, coordinator, cavity)
            for cavity in supported_cavities
            if appliance_data.is_cavity_feature_supported(cavity, ALERTS)
        )

        if appliance_data.is_feature_supported(ALERTS):
            entities.append(
                ApplianceAlertSensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

    if isinstance(appliance_data, HDAppliance):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in HOOD_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        if appliance_data.is_feature_supported(ALERTS):
            entities.append(
                ApplianceAlertSensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

    if isinstance(appliance_data, HBAppliance):
        entities.extend(
            ElectroluxSensor(appliance_data, coordinator, description)
            for description in HOB_ELECTROLUX_SENSORS
            if description.is_supported_fn(appliance_data)
        )

        if appliance_data.is_feature_supported(ALERTS):
            entities.append(
                ApplianceAlertSensor(
                    appliance_data=appliance_data,
                    coordinator=coordinator,
                )
            )

        for hob_zone in appliance_data.get_available_hob_zone():
            entities.extend(
                ElectroluxHobZoneSensor(
                    appliance_data, hob_zone, coordinator, description
                )
                for description in HOB_ZONE_ELECTROLUX_SENSORS
                if description.is_supported_fn(appliance_data, hob_zone)
            )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set sensor for Electrolux Integration."""
    await async_setup_entities_helper(
        hass, entry, async_add_entities, build_entities_for_appliance
    )


class AirPurifierAirQualitySensor(ElectroluxBaseEntity[APAppliance], SensorEntity):
    """Representation of the Air Purifier Air quality."""

    def __init__(
        self,
        appliance_data: APAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
        property: str,
    ) -> None:
        """Initialize the Air quality sensor."""
        super().__init__(appliance_data, coordinator)
        self._property_name = property
        self._attr_name = SENSOR_TYPES[property]["name"]
        self._attr_native_unit_of_measurement = SENSOR_TYPES[property]["unit"]
        self._attr_device_class = SENSOR_TYPES[property]["device_class"]
        self._attr_state_class = "measurement"
        self._attr_unique_id = f"{appliance_data.appliance.applianceId}_{property}"
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_value = self._get_value()

    def _get_value(self) -> float:
        return self._appliance_data.get_current_air_quality(self._property_name)


class RVCBatterySensor(ElectroluxBaseEntity[RVCAppliance], SensorEntity):
    """Representation of the RVC Battery."""

    def __init__(
        self, appliance_data: RVCAppliance, coordinator: ElectroluxDataUpdateCoordinator
    ) -> None:
        """Initialize the Battery sensor."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Battery"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = "measurement"
        self._attr_unique_id = f"{appliance_data.appliance.applianceId}_{property}"
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_value = self._get_value()

    def _get_value(self) -> int:
        return self._appliance_data.get_battery_percentage()


class ElectroluxSensor(ElectroluxBaseEntity[ApplianceData], SensorEntity):
    """Representation of a generic sensor for Electrolux appliances."""

    def __init__(
        self,
        appliance_data: ApplianceData,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(appliance_data, coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = getattr(
            description, "native_unit_of_measurement", None
        )
        self._attr_suggested_unit_of_measurement = getattr(
            description, "suggested_unit_of_measurement", None
        )
        self._attr_state_class = getattr(description, "state_class", None)
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.key}"
        )
        self._value_fn = description.value_fn
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_value = self._get_value()

    def _get_value(self) -> Any:
        return self._value_fn(self._appliance_data)


class ElectroluxCavitySensor(ElectroluxBaseEntity[ApplianceData], SensorEntity):
    """Representation of a generic sensor for appliance cavities."""

    def __init__(
        self,
        appliance_data: ApplianceData,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity: str,
        description: ElectroluxSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(appliance_data, coordinator)
        self._cavity = cavity
        self.entity_description = description
        self._attr_name = f"{cavity} - {description.name}"
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = getattr(
            description, "native_unit_of_measurement", None
        )
        self._attr_suggested_unit_of_measurement = getattr(
            description, "suggested_unit_of_measurement", None
        )
        self._attr_state_class = getattr(description, "state_class", None)
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.key}_{cavity}"
        )
        self._value_fn = description.value_fn
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_value = self._get_value()

    def _get_value(self) -> Any:
        return self._value_fn(self._appliance_data, self._cavity)


class ElectroluxTemperatureSensor(ElectroluxSensor):
    """Representation of a temperature sensor for Electrolux appliances."""

    def __init__(
        self,
        appliance_data: ApplianceData,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(appliance_data, coordinator, description)
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = "measurement"
        self._appliance = cast(OVAppliance | CRAppliance, appliance_data)
        self._attr_native_unit_of_measurement = ELECTROLUX_TO_HA_TEMPERATURE_UNIT.get(
            self._appliance.get_current_temperature_unit()
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_value = self._get_value()

    def _get_value(self) -> Any:
        return self._value_fn(self._appliance_data)


class ElectroluxTemperatureCavitySensor(ElectroluxSensor):
    """Representation of a temperature cavity sensor for Electrolux appliances."""

    def __init__(
        self,
        appliance_data: SOAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity: str,
        description: ElectroluxSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        self._cavity = cavity
        super().__init__(appliance_data, coordinator, description)
        self._attr_name = f"{cavity} - {description.name}"
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{description.key}_{cavity}"
        )
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = "measurement"
        self._attr_native_unit_of_measurement = ELECTROLUX_TO_HA_TEMPERATURE_UNIT.get(
            appliance_data.get_current_temperature_unit()
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_value = self._get_value()

    def _get_value(self) -> Any:
        return self._value_fn(self._appliance_data, self._cavity)


class ApplianceAlertSensor(ElectroluxBaseEntity[ApplianceData], SensorEntity):
    """Representation of appliance alerts."""

    def __init__(
        self,
        appliance_data: ApplianceData,
        coordinator: ElectroluxDataUpdateCoordinator,
    ) -> None:
        """Initialize the alerts sensor."""
        super().__init__(appliance_data, coordinator)
        self._attr_name = "Alerts"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_unique_id = f"{appliance_data.appliance.applianceId}_alerts"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._appliance = cast(
            WMAppliance
            | WDAppliance
            | TDAppliance
            | DWAppliance
            | OVAppliance
            | SOAppliance
            | CRAppliance
            | HDAppliance
            | HBAppliance,
            appliance_data,
        )
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        alerts = self._get_value()
        if alerts:
            self._attr_native_value = f"{len(alerts)} alert(s)"
            self._attr_extra_state_attributes = {
                f"alert_{i + 1}": {
                    "code": alert["code"],
                    "severity": alert["severity"],
                    "acknowledge_status": alert["acknowledgeStatus"],
                }
                for i, alert in enumerate(alerts)
            }
        else:
            self._attr_native_value = "No alerts"
            self._attr_extra_state_attributes = {}

    def _get_value(self) -> Any:
        return self._appliance.get_current_alerts()


class ApplianceAlertCavitySensor(ElectroluxBaseEntity[ApplianceData], SensorEntity):
    """Representation of appliance cavity alerts."""

    def __init__(
        self,
        appliance_data: CRAppliance,
        coordinator: ElectroluxDataUpdateCoordinator,
        cavity,
    ) -> None:
        """Initialize the alerts sensor."""
        super().__init__(appliance_data, coordinator)
        self._cavity = cavity
        self._attr_name = f"{cavity} - alerts"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_unique_id = f"{appliance_data.appliance.applianceId}_alerts_{cavity}"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._appliance_data = appliance_data
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        alerts = self._get_value()
        if alerts:
            self._attr_native_value = f"{len(alerts)} alert(s)"
            self._attr_extra_state_attributes = {
                f"alert_{i + 1}": {
                    "code": alert["code"],
                    "severity": alert["severity"],
                    "acknowledge_status": alert["acknowledgeStatus"],
                }
                for i, alert in enumerate(alerts)
            }
        else:
            self._attr_native_value = "No alerts"
            self._attr_extra_state_attributes = {}

    def _get_value(self) -> Any:
        return self._appliance_data.get_current_cavity_alerts(self._cavity)


class ElectroluxHobZoneSensor(ElectroluxBaseEntity[HBAppliance], SensorEntity):
    """Representation of a generic sensor for hob zones appliances."""

    def __init__(
        self,
        appliance_data: HBAppliance,
        hob_zone: str,
        coordinator: ElectroluxDataUpdateCoordinator,
        description: ElectroluxSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(appliance_data, coordinator)
        self.entity_description = description
        self._hob_zone = hob_zone
        self._attr_name = f"{hob_zone} - {description.name}"
        self._attr_icon = HOB_ZONE_TO_ICON_MAP.get(hob_zone, "mdi:gas-burner")
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = getattr(
            description, "native_unit_of_measurement", None
        )
        self._attr_suggested_unit_of_measurement = getattr(
            description, "suggested_unit_of_measurement", None
        )
        self._attr_state_class = getattr(description, "state_class", None)
        self._attr_unique_id = (
            f"{appliance_data.appliance.applianceId}_{hob_zone}_{description.key}"
        )
        self._value_fn = description.value_fn
        self._update_attr_state()

    def _update_attr_state(self) -> None:
        self._attr_native_value = self._get_value()

    def _get_value(self) -> Any:
        return self._value_fn(self._appliance_data, self._hob_zone)
