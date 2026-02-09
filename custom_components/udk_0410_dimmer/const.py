"""Constants for UDK-04-10 Dimmer (RS-485/DMX)."""

DOMAIN = "udk_0410_dimmer"

CONF_PORT = "port"
CONF_BAUDRATE = "baudrate"

# Stored in options: list of modules
CONF_MODULES = "modules"
CONF_MODULE_NAME = "name"
CONF_ADDRESS = "address"

# per-module channel names
CONF_CH1_NAME = "ch1_name"
CONF_CH2_NAME = "ch2_name"
CONF_CH3_NAME = "ch3_name"
CONF_CH4_NAME = "ch4_name"

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUDRATE = 38400
