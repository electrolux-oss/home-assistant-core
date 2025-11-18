"""Constants for Electrolux Group integration."""

from homeassistant.const import __version__ as HA_VERSION

DOMAIN = "electrolux_group"

GET_INTERACTIVE_MAPS_SERVICE_NAME = "getInteractiveMaps"
GET_MEMORY_MAPS_SERVICE_NAME = "getMemoryMaps"

CONF_REFRESH_TOKEN = "refresh_token"

DEFAULT_SCAN_INTERVAL = 30

ATTR_CONFIG_ENTITY_ID = "entity_id"

NEW_APPLIANCE = "electrolux_new_appliance"

ELECTROLUX_INTEGRATION_VERSION = "0.0.1"

USER_AGENT = f"HomeAssistant/{HA_VERSION} ElectroluxGroupIntegration/{ELECTROLUX_INTEGRATION_VERSION}"
