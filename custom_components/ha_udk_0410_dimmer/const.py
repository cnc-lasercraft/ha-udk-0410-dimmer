from __future__ import annotations

DOMAIN = "ha_udk_0410_dimmer"

CONF_PORT = "port"
CONF_BAUDRATE = "baudrate"

CONF_MODULES = "modules"  # stored in entry.options
# Module dict keys
MOD_NAME = "name"
MOD_ADDRESS = "address"
MOD_DIMMERS = "dimmers"  # list of 4 dicts {index, name}
