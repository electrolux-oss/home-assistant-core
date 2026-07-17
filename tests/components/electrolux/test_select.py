"""Select tests of Electrolux integration."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, call, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import get_appliance_id, merge_dict_recursive, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS."""
    with patch("homeassistant.components.electrolux.PLATFORMS", [Platform.SELECT]):
        yield


@pytest.mark.usefixtures("appliances")
async def test_select(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test states of the select."""
    await setup_integration(hass, mock_config_entry)
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    (
        "appliance_fixture",
        "entity_id",
        "appliance_state",
    ),
    [
        (
            "tumble_dryer",
            "select.dryer_program",
            {},
        ),
    ],
)
@pytest.mark.parametrize(
    ("option", "commands"),
    [
        (
            "BED_LINEN_PLUS_PR_BEDDINGPLUS",
            [{"userSelections": {"programUID": "BED_LINEN_PLUS_PR_BEDDINGPLUS"}}],
        ),
        (
            "COTTON_PR_COTTONS",
            [{"userSelections": {"programUID": "COTTON_PR_COTTONS"}}],
        ),
        (
            "COTTON_PR_ENERGYSAVER",
            [{"userSelections": {"programUID": "COTTON_PR_ENERGYSAVER"}}],
        ),
        (
            "DRY_CLEANING_PR_REFRESH",
            [{"userSelections": {"programUID": "DRY_CLEANING_PR_REFRESH"}}],
        ),
        ("DUVET_PR_DUVET", [{"userSelections": {"programUID": "DUVET_PR_DUVET"}}]),
        (
            "EXTRA_DELICATE_PR_DELICATES",
            [{"userSelections": {"programUID": "EXTRA_DELICATE_PR_DELICATES"}}],
        ),
        ("JEANS_PR_DENIM", [{"userSelections": {"programUID": "JEANS_PR_DENIM"}}]),
        (
            "OUTD_PROOF_PR_OUTDOOR",
            [{"userSelections": {"programUID": "OUTD_PROOF_PR_OUTDOOR"}}],
        ),
        ("SILK_DRY_PR_SILK", [{"userSelections": {"programUID": "SILK_DRY_PR_SILK"}}]),
        ("SPORTS_PR_SPORT", [{"userSelections": {"programUID": "SPORTS_PR_SPORT"}}]),
        (
            "SYNTHETIC_PR_SYNTHETICS",
            [{"userSelections": {"programUID": "SYNTHETIC_PR_SYNTHETICS"}}],
        ),
        (
            "TIMEDRY_PR_DRYINGRACK",
            [{"userSelections": {"programUID": "TIMEDRY_PR_DRYINGRACK"}}],
        ),
        (
            "UNIVERSAL_PR_MIXEDPLUSNOTXL",
            [{"userSelections": {"programUID": "UNIVERSAL_PR_MIXEDPLUSNOTXL"}}],
        ),
        (
            "WOOL_GOLD_PR_WOOL",
            [{"userSelections": {"programUID": "WOOL_GOLD_PR_WOOL"}}],
        ),
    ],
)
async def test_select_dryer_program(
    hass: HomeAssistant,
    appliances: AsyncMock,
    appliance_fixture: str,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    appliance_state: dict[str, Any],
    option: str,
    commands: list[dict[str, Any]],
) -> None:
    """Test dryer program commands."""

    await command_test(
        hass,
        appliances,
        appliance_fixture,
        mock_config_entry,
        entity_id,
        appliance_state,
        {ATTR_OPTION: option},
        commands,
    )


@pytest.mark.parametrize(
    (
        "appliance_fixture",
        "entity_id",
        "appliance_state",
    ),
    [
        (
            "fenix_oven",
            "select.fenix_program",
            {},
        ),
    ],
)
@pytest.mark.parametrize(
    ("option", "commands"),
    [
        (
            "AIR_SOUS_VIDE",
            [{"program": "AIR_SOUS_VIDE"}],
        ),
        (
            "BOTTOM",
            [{"program": "BOTTOM"}],
        ),
        (
            "GRILL",
            [{"program": "GRILL"}],
        ),
        (
            "GRILL_FAN",
            [{"program": "GRILL_FAN"}],
        ),
        (
            "PIZZA",
            [{"program": "PIZZA"}],
        ),
    ],
)
async def test_select_oven_program(
    hass: HomeAssistant,
    appliances: AsyncMock,
    appliance_fixture: str,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    appliance_state: dict[str, Any],
    option: str,
    commands: list[dict[str, Any]],
) -> None:
    """Test oven program commands."""

    await command_test(
        hass,
        appliances,
        appliance_fixture,
        mock_config_entry,
        entity_id,
        appliance_state,
        {ATTR_OPTION: option},
        commands,
    )


@pytest.mark.parametrize(
    (
        "appliance_fixture",
        "entity_id",
        "appliance_state",
    ),
    [
        (
            "supex_structured_oven",
            "select.supex_oven_upper_cavity_program",
            {},
        ),
    ],
)
@pytest.mark.parametrize(
    ("option", "commands"),
    [
        (
            "BAKE",
            [{"upperOven": {"program": "BAKE"}}],
        ),
        (
            "BROIL",
            [{"upperOven": {"program": "BROIL"}}],
        ),
        (
            "TRUE_FAN",
            [{"upperOven": {"program": "TRUE_FAN"}}],
        ),
    ],
)
async def test_select_structured_oven_program(
    hass: HomeAssistant,
    appliances: AsyncMock,
    appliance_fixture: str,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    appliance_state: dict[str, Any],
    option: str,
    commands: list[dict[str, Any]],
) -> None:
    """Test structured oven program commands."""

    await command_test(
        hass,
        appliances,
        appliance_fixture,
        mock_config_entry,
        entity_id,
        appliance_state,
        {ATTR_OPTION: option},
        commands,
    )


@pytest.mark.parametrize(
    (
        "appliance_fixture",
        "appliance_state",
    ),
    [
        (
            "peacock_hob",
            {},
        ),
    ],
)
@pytest.mark.parametrize(
    ("entity_id", "option", "commands"),
    [
        # fan speed tests
        (
            "select.peacock_hob_hood_fan_speed",
            "STEP_1",
            [{"hobHood": {"hobToHoodFanSpeed": "STEP_1"}}],
        ),
        (
            "select.peacock_hob_hood_fan_speed",
            "STEP_2",
            [{"hobHood": {"hobToHoodFanSpeed": "STEP_2"}}],
        ),
        (
            "select.peacock_hob_hood_fan_speed",
            "STEP_3",
            [{"hobHood": {"hobToHoodFanSpeed": "STEP_3"}}],
        ),
        # hood state tests
        (
            "select.peacock_hob_hood_state",
            "AUTOMATIC",
            [{"hobHood": {"hobToHoodState": "AUTOMATIC"}}],
        ),
        (
            "select.peacock_hob_hood_state",
            "MANUAL",
            [{"hobHood": {"hobToHoodState": "MANUAL"}}],
        ),
    ],
)
async def test_select_hob(
    hass: HomeAssistant,
    appliances: AsyncMock,
    appliance_fixture: str,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    appliance_state: dict[str, Any],
    option: str,
    commands: list[dict[str, Any]],
) -> None:
    """Test hob commands."""

    await command_test(
        hass,
        appliances,
        appliance_fixture,
        mock_config_entry,
        entity_id,
        appliance_state,
        {ATTR_OPTION: option},
        commands,
    )


@pytest.mark.parametrize(
    (
        "appliance_fixture",
        "appliance_state",
    ),
    [
        (
            "hood",
            {},
        ),
    ],
)
@pytest.mark.parametrize(
    ("entity_id", "option", "commands"),
    [
        # fan level tests
        (
            "select.ceiling_hood_fan_level",
            "STEP_1",
            [{"hoodFanLevel": "STEP_1"}],
        ),
        (
            "select.ceiling_hood_fan_level",
            "STEP_2",
            [{"hoodFanLevel": "STEP_2"}],
        ),
        (
            "select.ceiling_hood_fan_level",
            "STEP_3",
            [{"hoodFanLevel": "STEP_3"}],
        ),
    ],
)
async def test_select_hood(
    hass: HomeAssistant,
    appliances: AsyncMock,
    appliance_fixture: str,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    appliance_state: dict[str, Any],
    option: str,
    commands: list[dict[str, Any]],
) -> None:
    """Test hob commands."""

    await command_test(
        hass,
        appliances,
        appliance_fixture,
        mock_config_entry,
        entity_id,
        appliance_state,
        {ATTR_OPTION: option},
        commands,
    )


async def command_test(
    hass: HomeAssistant,
    appliances: AsyncMock,
    appliance_fixture: str,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    appliance_state: dict[str, Any],
    data: dict[str, Any],
    commands: list[dict[str, Any]],
) -> None:
    """Test command."""

    appliance_id = get_appliance_id(appliance_fixture)

    state = await appliances.get_appliance_state(appliance_id)
    state.properties["reported"] = merge_dict_recursive(
        state.properties["reported"], appliance_state
    )

    appliances.get_appliance_state.side_effect = None
    appliances.get_appliance_state.return_value = state

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id} | data,
        blocking=True,
    )
    assert appliances.send_command.mock_calls == [
        call(appliance_id, command) for command in commands
    ]
