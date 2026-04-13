# Fragen für Hersteller-Besuch — 18. April 2026

## Protokoll

1. **Parameterblock lesen** — Command 0x42 schreibt den Parameterblock. Gibt es einen Read-Command um die 250 Bytes auszulesen? (Dimm-Kurven, Min/Max, Master/Slave-Kopplung, Lastart etc.)

2. **Module M12, M14, M15 antworten nicht auf 0x53** (Statusabfrage) — ältere Firmware? Oder anderer Grund?

3. **Brightness-Wertebereich** — Protokoll sagt Data 0x00-0xFD, unsere Integration sendet bis 0xFF (255). Funktioniert, aber ist das korrekt? Was liefert die Statusabfrage maximal zurück?

## Features

4. **Kanal-Kopplung (Master/Slave)** — Byte 5 Bit 4/5 im Parameterblock. Wie wird das in der Praxis konfiguriert? Nur über Parameterblock-Write, oder gibt es einen einfacheren Weg?

5. **Dimm-Kurven** — linear, log, quadratisch, schalten, User-Kurven. Wie werden diese typischerweise gewählt? Gibt es Empfehlungen pro Lasttyp (LED, Halogen, etc.)?

6. **Notbetrieb-Eingänge** — Byte 3 (flash_notbetriebsinput). Was genau passiert bei Notbetrieb? Klemme auf +UB = Kanal aktiv?

## Integration / Zusammenarbeit

7. **Interesse an HACS-Veröffentlichung?** — Die CC ist auf GitHub: github.com/cnc-lasercraft/ha_udk-0410-dimmer. Wäre eine offizielle Empfehlung/Verlinkung denkbar?

8. **Firmware-Versionen** — Gibt es unterschiedliche Firmware-Stände im Feld? Unterschiede im Protokoll-Support (z.B. 0x53 nicht bei allen)?

9. **Weitere RS-485 Produkte** — Gibt es andere Geräte (Schaltaktoren, Sensoren) mit dem gleichen Protokoll die man anbinden könnte?

10. **Logo-Nutzung** — Dürfen wir das varintens/se-Lightmanagement-Logo als Icon für die Integration verwenden? (Aktuell "icon not available" in HA)
