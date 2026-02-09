# UDK-04-10 Dimmer – Home Assistant Integration

Integration for **SE Lightmanagement AG** dimmer module **UDK-04-10** (RS-485/DMX).
One module always contains **4 dimmer channels**.

## UI setup (recommended)
**Settings → Devices & services → Add integration → UDK-04-10 Dimmer**

Add **one entry per module** (M01, M02, …) with:
- Address (1..)
- Serial port (e.g. `/dev/ttyUSB0`)
- Baudrate (default 38400)

After adding a module, you can set the 4 channel names via:
**Integration → Configure (Options)**

## Legacy YAML example
```yaml
light:
  - platform: udk_0410_dimmer
    modules:
      - name: "M01"
        address: 1
        port: "/dev/ttyUSB0"
        baudrate: 38400
        dimmers:
          - name: "SW Garagenplatz"
            index: 1
          - name: "Steckdose Zi EG"
            index: 2
          - name: "Entree 1"
            index: 3
          - name: "Esstisch"
            index: 4
```

## Notes
- Entity IDs can still be renamed in Home Assistant (Entity Registry).
- If you run multiple modules on the same RS-485 adapter, they share the same serial connection (per port+baudrate).
