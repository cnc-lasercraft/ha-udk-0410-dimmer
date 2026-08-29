# HA UDK-0410 Dimmer (RS485)

![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-blue)
![Version](https://img.shields.io/badge/version-1.2.0-green)

Home Assistant custom integration for the **UDK-0410 RS485 dimmer modules** (4 channels per module).

This integration creates **one Light entity per channel** and supports:
- Brightness control
- Transitions
- Reliable ACK-based communication with retry
- Full UI setup via Config Flow (no YAML required)
- Custom Lovelace card for module management

---

## Features

- Multi-module support (each module = 4 dimmer channels)
- All modules share the same RS485 serial bus
- One `light` entity per channel
- Brightness + transitions supported
- ACK handling with automatic retry (3 attempts)
- Custom dashboard card for adding, editing, and removing modules
- Services for programmatic module management
- Easy setup via Home Assistant UI

---

## Quick Start

1. Install the integration (HACS or manual)
2. Restart Home Assistant
3. Add the integration in the UI
4. Configure your serial port and baudrate
5. Add modules via the options flow or the custom card

---

## Installation

### Option A — HACS (recommended)

1. Open **HACS > Integrations**
2. Menu > **Custom repositories**
3. Add: `https://github.com/cnc-lasercraft/ha_udk-0410-dimmer`
4. Category: **Integration**
5. Install **UDK-04-10 Dimmer**
6. Restart Home Assistant

### Option B — Manual

Copy `custom_components/ha_udk_0410_dimmer` to your Home Assistant `/config/custom_components/` directory and restart.

---

## Setup

Go to **Settings > Devices & Services > Add Integration** and search for **UDK-04-10 Dimmer**.

### Serial settings

| Setting  | Default | Example                                                              |
|----------|---------|----------------------------------------------------------------------|
| Port     | —       | `/dev/ttyUSB0` or `/dev/serial/by-id/usb-FTDI_FT232R_USB_UART-...` |
| Baudrate | 38400   | 38400                                                                |

---

## Adding Modules

Each module contains **4 dimmer channels**. Modules can be added in three ways:

1. **Options flow**: Settings > Devices & Services > UDK-04-10 Dimmer > Configure
2. **Custom card**: Add the `udk-dimmer-card` to your dashboard (see below)
3. **Service call**: Use `ha_udk_0410_dimmer.add_module`

For each module you configure:
- RS485 address (1–247)
- Module name (e.g. `M01`)
- Channel names (Dimmer 1–4)

> **Note:** Renaming modules or channels only changes the display name (`friendly_name`).
> The `entity_id` (e.g. `light.m01d1_sw_garagenplatz`) stays the same — automations and scenes are not affected.

---

## Custom Card

The integration includes a Lovelace card for managing modules directly from the dashboard.

### Installation

1. Copy `cards/udk-dimmer-card.js` to `/config/www/udk-dimmer-card.js`
2. Add as dashboard resource: `/local/udk-dimmer-card.js` (type: JavaScript Module)
3. Add a manual card with type `custom:udk-dimmer-card`

### Card configuration

```yaml
type: custom:udk-dimmer-card
config_entity: sensor.udk_04_10_dimmer_dimmer_config
```

The card allows adding, renaming, and removing modules — changes are saved immediately.

---

## Services

### `ha_udk_0410_dimmer.add_module`

Add a new dimmer module. Creates 4 channels and reloads the integration.

| Field   | Required | Description                          |
|---------|----------|--------------------------------------|
| address | yes      | RS-485 module address (1–247)        |
| name    | no       | Module name (default: M01, M02, ...) |

### `ha_udk_0410_dimmer.update_module`

Update a module or channel name.

| Field   | Required | Description                                          |
|---------|----------|------------------------------------------------------|
| address | yes      | RS-485 module address (1–247)                        |
| key     | yes      | `name` for module name, `d1`–`d4` for channel names |
| value   | yes      | New value                                            |

### `ha_udk_0410_dimmer.remove_module`

Remove a module and its channels. Reloads the integration.

| Field   | Required | Description                     |
|---------|----------|---------------------------------|
| address | yes      | RS-485 module address to remove |

---

## Entities

### Light entities

Each channel is exposed as a `light` entity with brightness and transition support.

### Config sensor

A `sensor` entity exposes the current module configuration as attributes, used by the custom card.

---

## Logging

To enable debug logging add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ha_udk_0410_dimmer: debug
```

---

## Troubleshooting

### Entities don't appear after adding a module
- Check that the integration reloaded (a full HA restart may be needed)
- Check logs for `custom_components.ha_udk_0410_dimmer`

### Serial connection issues
- Verify the serial port exists: `ls /dev/ttyUSB*` or `ls /dev/serial/by-id/`
- Check that no other process is using the port

### No response from modules (no ACK)
- Verify RS-485 wiring (A/B lines, termination)
- Check module address matches configuration
- Enable debug logging to see sent/received hex data

---

## License

MIT — see [LICENSE](LICENSE).
