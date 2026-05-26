# Bug: Status-Polling liefert unvollständige Frames → Phantom-States

**Datum:** 2026-05-26
**Datei:** `custom_components/ha_udk_0410_dimmer/light.py`
**Schweregrad:** Mittel — funktional, aber Anzeige-State unzuverlässig; Folge-Probleme in Toggle-Logik möglich

## Symptom

Light-Entities springen in Home Assistant zwischen `on` und `off` ohne dass ein Service-Call oder Skript dafür verantwortlich ist. Der `last_changed` State-Change kommt **ohne `context_event_type`** im Logbook (= Polling-Update, nicht User-getrieben).

Beobachtet z.B.:
- 31 s nach `turn_on(brightness=74)` springt der State auf `off` obwohl Lampe physisch an
- 15 s nach `turn_off` springt der State auf `on` obwohl Lampe physisch aus

## Reproduktion

1. `scene.turn_on` auf eine Light-Group mit UDK-Lampen → alle Mitglieder gehen physisch an, HA-State `on`
2. ~30 s warten (länger als `_last_command_time < 5.0` Schutzfenster)
3. HA-State der UDK-Dimmer springt spontan auf `off`, Lampen bleiben physisch an
4. Folgeeffekt: Master Dimmer/Toggle-Logik im User-Stack interpretiert nun falsch und macht z.B. beim nächsten Tasterdruck das Falsche

## Beweis (DEBUG-Logs)

Status-Query und Response für mehrere Module (DEBUG-Log, Auszug 2026-05-26 06:28:46):

```
RS485: Sende (hex): fffe03530f0065ff
RS485: Match gefunden (fe0353) im Buffer (12 bytes): 00fffe035300000000000000

RS485: Sende (hex): fffe04530f0066ff
RS485: Match gefunden (fe0453) im Buffer (10 bytes): 00fffe04530000000000

RS485: Sende (hex): fffe0b530f006dff
RS485: Match gefunden (fe0b53) im Buffer (12 bytes): 00fffe0b5300000000000000
```

**Beobachtung:** Buffer enthält Prefix `FE <addr> 53` bei Position 2 (vorne hängen `00 FF` aus dem ACK-Trailer des vorherigen Frames). Insgesamt liegt der Buffer bei 8–15 Bytes, aber **das Stop-Byte `0xFF` des aktuellen Frames fehlt durchgängig**. Damit liefert das Modul entweder kein vollständiges Frame, oder `send_and_wait_for` returnt zu früh — siehe Code-Analyse.

## Code-Analyse

### Bug 1 — `send_and_wait_for` returnt sofort beim Pattern-Match

`light.py:115-141`

```python
while time.monotonic() < deadline:
    ...
    chunk = await asyncio.wait_for(self._reader.read(1024), timeout=chunk_timeout)
    ...
    if chunk:
        buf.extend(chunk)
        ...
        for p in patterns:
            if p in buf:
                ...
                return bytes(buf), p    # ← returnt sofort, ohne auf Frame-Ende zu warten
```

Pattern ist hier `FE <addr> 53` (nur 3 Bytes). Sobald diese drei Bytes im Buffer auftauchen, wird zurückgekehrt — auch wenn die restlichen 9 Bytes des Frames (`D0..D7 FF`) noch nicht gelesen wurden.

### Bug 2 — `_parse_status_response` schlägt fast immer fehl

`light.py:365-380`

```python
def _parse_status_response(self, buf: bytes) -> bytes | None:
    prefix = bytes([self.START_BYTE, self.module_address, self.CMD_STATUS])
    if prefix not in buf:
        return None
    idx = buf.index(prefix)
    # Need prefix(3) + data(8) + end(1) = 12 bytes
    if idx + 12 > len(buf):
        return None
    if buf[idx + 11] != 0xFF:
        return None
    return buf[idx + 3 : idx + 11]
```

Bei `idx=2` und `len(buf)=12` ist `2 + 12 = 14 > 12` → `return None`. **In sämtlichen beobachteten Frames trifft dieser Pfad zu** — der Parser liefert nie gültige Daten.

### Folgefehler in `async_update`

`light.py:393-431`

```python
if matched:
    data = self._parse_status_response(buf)
    if data:
        self.hass.data[cache_key] = {"poll_time": now, "data": data}
        self._apply_status(data)
        return

# Poll failed — mark as polled (don't retry this cycle) and use old data
if cache:
    cache["poll_time"] = now
    self._apply_status(cache["data"])    # ← wendet altes/stale data an
```

Wenn der Cache vorher mal mit Daten gefüllt wurde (selten, nur wenn ein Frame zufällig vollständig im Buffer lag), wird `_apply_status(cache["data"])` mit diesen alten Daten aufgerufen. Da `_apply_status` (`light.py:382-391`) setzt:

```python
self._brightness = level
self._is_on = level > 0
```

springt der HA-State auf den ge-cachten alten Wert, unabhängig vom aktuellen Modul-Zustand. → **Phantom-States** in beide Richtungen.

## Wurzel

**Race-Condition im Frame-Lesen:** Das Pattern (`FE addr 53`, 3 Bytes) wird als "Match" gewertet, ohne dass die restlichen 9 Bytes des 12-Byte-Frames bereits im Buffer angekommen sind. `_parse_status_response` braucht aber den vollständigen Frame inkl. `FF` Stop-Byte. Damit scheitert der Parser systematisch, und der Fallback-Pfad nutzt stale Cache-Daten.

## Fix-Optionen

### Option A — Mindestlänge nach Match (klein, lokal in `send_and_wait_for`)

Nach Pattern-Match noch warten bis mindestens N weitere Bytes da sind (oder Timeout):

```python
for p in patterns:
    if p in buf:
        idx = buf.index(p)
        needed = idx + 12  # für Status-Response; ACK braucht idx+4
        if len(buf) >= needed:
            return bytes(buf), p
        # else: weiterlesen
```

Problem: `send_and_wait_for` kennt das Frame-Format nicht abstrakt. Mögliche Lösung: zusätzlicher Parameter `min_bytes_after_pattern` pro Aufruf.

### Option B — Pattern inkl. Stop-Byte erweitern

Statt `FE addr 53` als Pattern auf `FE addr 53 .{8} FF` (regex) matchen — geht nur mit eigenem Scan-Loop, nicht mit `bytes.in`.

### Option C — Defer-Parse im `async_update`

In `async_update` nach dem `send_and_wait_for` aktiv weiterlesen bis ein vollständiger 12-Byte-Frame ab dem Prefix vorliegt, dann erst parsen.

### Option D — Stale-Cache abschalten

Im "Poll failed"-Pfad **nicht** `_apply_status(cache["data"])` aufrufen. Damit bleibt der State unverändert beim letzten Set-Befehl, statt auf stale Polling-Daten zu springen. Verhindert nicht die Wurzel, eliminiert aber das Symptom.

## Empfehlung

**Option A + D kombiniert.** A löst die Wurzel sauber, D ist defensive in depth. Mit DEBUG-Logs verifizieren, dass nach dem Fix die Frames vollständig geparst werden.

## Status

- 2026-05-26: Diagnose abgeschlossen, in diesem Dokument festgehalten
- 2026-05-26: Fix implementiert (Option A + D) in `light.py`
  - `send_and_wait_for` hat neuen Parameter `min_frame_len`. Nach Pattern-Match wird weitergelesen, bis ab Pattern-Start mindestens `min_frame_len` Bytes im Buffer liegen.
  - `async_update` ruft Polling mit `min_frame_len=12` → wartet auf vollständiges 12-Byte-Status-Frame inkl. `FF`-Stop-Byte.
  - Im Poll-Fail-Pfad wird `_apply_status(cache["data"])` **nicht mehr** aufgerufen — der HA-State bleibt unverändert beim letzten gesetzten Wert. Verhindert Phantom-on/off-Sprünge.
  - ACK-Pfad (`sende_befehl_mit_ack`) bleibt unverändert: ACK-Pattern ist bereits 4 Bytes inkl. Stop-Byte.
- Aktiviert nach HA-Core-Restart. Verifikation: DEBUG-Log soll nach Restart `Status OK` Einträge zeigen statt nur Match+Stale-Cache.
