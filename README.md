# HA UDK-0410 Dimmer (RS485)

![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-blue)

Home Assistant custom integration for the **UDK-0410 RS485 dimmer modules** (4 channels per module).

This integration creates **one Light entity per channel** and supports:
- Brightness control
- Transitions
- Reliable ACK-based communication
- Full UI setup via Config Flow (no YAML required)

---

## 📸 Screenshots

Add your screenshots here:

- `docs/setup.png`
- `docs/modules.png`

<p float="left">
  <img src="docs/setup.png" width="48%" />
  <img src="docs/modules.png" width="48%" />
</p>

---

## ✨ Features

- ✅ Multi-module support (each module = 4 dimmer channels)
- ✅ All modules share the same RS485 serial bus
- ✅ One `light` entity per channel
- ✅ Brightness + transitions supported
- ✅ ACK handling for more reliable control
- ✅ Easy setup via Home Assistant UI

---

## 🚀 Quick Start

1. Install the integration (HACS or manual)
2. Restart Home Assistant
3. Add the integration in the UI
4. Configure your modules and channel names

---

## 📦 Installation

### Option A — HACS (recommended)

1. Open **HACS → Integrations**
2. Menu (⋮) → **Custom repositories**
3. Add your GitHub repo URL
4. Category: **Integration**
5. Install **HA UDK-0410 Dimmer**
6. Restart Home Assistant

---

### Option B — Manual

Copy:

```
custom_components/ha_udk_0410_dimmer
```

to:

```
/config/custom_components/
```

Restart Home Assistant.

---

## ⚙️ Setup (UI)

Go to:

**Settings → Devices & Services → Add Integration**

Search for:

**HA UDK-0410 Dimmer**

Then enter your serial settings.

### Serial settings

| Setting | Default | Example |
|--------|---------|---------|
| Port | — | `/dev/ttyUSB0` |
| Baudrate | `38400` | `38400` |

---

## 🧩 Adding Modules

Each module contains **4 dimmer channels**.

In the configuration you enter:

- Module name (example: `M01`)
- RS485 address (example: `1`)
- Channel 1 name
- Channel 2 name
- Channel 3 name
- Channel 4 name

After pressing **Submit**, entities are created immediately.

---

## 🏷️ Entities

Each channel is exposed as a Home Assistant `light` entity.

Supported features:

- Brightness
- Transition

---

## 🪵 Logging

Default logging includes important startup information.

To enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.ha_udk_0410_dimmer: debug
```

---

## 🛠️ Troubleshooting

### Entities don’t appear after adding a module

- Restart Home Assistant once after updating the integration
- Check logs for: `custom_components.ha_udk_0410_dimmer`

### Serial connection issues

Make sure your serial port exists, for example:

- `/dev/ttyUSB0`
- `/dev/serial/by-id/...`

---

## 📄 License

MIT License (recommended)

---

## 🧑‍💻 Development / Contributing

Bug reports and PRs are welcome.
