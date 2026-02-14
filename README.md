# UDK-04-10 Dimmer – Home Assistant Integration

Integration for .
HA UDK-0410 Dimmer (RS485)

A Home Assistant custom integration for the **SE Lightmanagement AG** dimmer module **UDK-04-10** (RS-485/DMX) (4 channels per module).

This integration creates one Light entity per dimmer channel and supports:

Brightness control

Transitions

Reliable ACK handling

Full UI setup via Config Flow (no YAML required)

✨ Features

✅ Supports multi-module setups (each module = 4 dimmers)

✅ All modules share one RS485 serial bus

✅ One Light entity per channel

✅ Brightness + transition support

✅ ACK-based sending (more reliable than fire-and-forget)

✅ Easy setup via Home Assistant UI

📦 Installation
Option A — HACS (recommended)

Open HACS → Integrations

Menu (⋮) → Custom repositories

Add your GitHub repo URL

Category: Integration

Install HA UDK-0410 Dimmer

Restart Home Assistant

Option B — Manual install

Copy:

custom_components/ha_udk_0410_dimmer


to:

/config/custom_components/


Restart Home Assistant.

⚙️ Setup (UI)

Go to:
Settings → Devices & Services → Add Integration

Search for:
HA UDK-0410 Dimmer

Enter:

Serial port (example: /dev/ttyUSB0)

Baudrate (default: 38400)

After setup, click Configure to add modules.

🧩 Adding Modules

Each module contains 4 dimmer channels.

In the module configuration you enter:

Module name (example: M01)

RS485 address (example: 1)

Channel 1 name

Channel 2 name

Channel 3 name

Channel 4 name

After pressing Submit, the entities are created immediately.

🏷️ Entities

Each channel is exposed as a Home Assistant light entity:

Supports brightness

Supports transitions

🪵 Logging

Default logging includes important startup information.

To enable debug logs, add to configuration.yaml:

logger:
  default: info
  logs:
    custom_components.ha_udk_0410_dimmer: debug

🛠️ Troubleshooting
Entities don’t appear after adding a module

Restart Home Assistant once after updating the integration

Check logs under:
custom_components.ha_udk_0410_dimmer

Serial connection issues

Make sure your serial port exists, for example:

/dev/ttyUSB0

/dev/serial/by-id/...

📄 License

MIT License (recommended)
