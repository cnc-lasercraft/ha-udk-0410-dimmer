# UDK-04-10 Dimmer – Home Assistant Integration

Integration for **SE Lightmanagement AG** dimmer module **UDK-04-10** (RS-485/DMX).

## UI setup (recommended)
**Settings → Devices & services → Add integration → UDK-04-10 Dimmer**

1) Create the **RS-485 bus** once:
- Port (e.g. `/dev/ttyUSB0`)
- Baudrate (default `38400`)

2) Go to **Configure (Options)** and add modules:
- Name (M01, M02, …)
- Address (1, 2, …)
- Channel names (1..4)

Each module always creates **4 light entities**.
