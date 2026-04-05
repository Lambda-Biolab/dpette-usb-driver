---
title: "System overview"
status: "DRAFT"
updated: "2026-04-06"
owner: "lambda biolab"
---

# System overview

## Physical architecture

```
┌──────────────────────────────────────────────────────────┐
│ Host PC                                                  │
│                                                          │
│  ┌──────────────────┐                                    │
│  │  dpette package   │  Python 3.11+                     │
│  │  ┌─────────────┐ │                                    │
│  │  │ driver.py    │ │  high-level commands               │
│  │  │  ↕           │ │                                    │
│  │  │ safety.py    │ │  parameter validation              │
│  │  │  ↕           │ │                                    │
│  │  │ protocol.py  │ │  frame encode / decode             │
│  │  │  ↕           │ │                                    │
│  │  │ serial_link  │ │  raw byte I/O                      │
│  │  └──────┬───────┘ │                                    │
│  └─────────┼─────────┘                                    │
│            │ pyserial                                     │
│            ▼                                              │
│    /dev/ttyUSB0                                           │
└────────────┬─────────────────────────────────────────────┘
             │ USB (CDC-ACM or vendor-specific)
             ▼
     ┌───────────────┐
     │ CP210x bridge │  Silicon Labs USB-UART
     └───────┬───────┘
             │ UART (TX/RX, baud TBD)
             ▼
     ┌───────────────┐
     │ Pipette MCU   │  microcontroller (unknown model)
     │               │
     │  ┌──────────┐ │
     │  │ Motor    │ │  stepper or DC motor driving piston
     │  │ driver   │ │
     │  └──────────┘ │
     └───────────────┘
```

## Project phases

### Phase 1 — Discovery

- Identify the CP210x VID/PID used by the dPette.
- Determine the baud rate, byte size, parity, and stop bits.
- Tool: `tools/scan_baud.py`.

### Phase 2 — Capture

- Record USB traffic between the vendor calibration software (Windows)
  and the pipette using USBPcap + Wireshark.
- Extract the serial-layer bytes from the USB bulk transfers.
- Store `.pcapng` files in `captures/`.
- Tool: `tools/capture_usb.py` (instructions), `tools/dump_raw.py`.

### Phase 3 — Analysis

- Identify packet framing: start byte(s), length field, type byte, payload, checksum.
- Map observed packets to physical operations (aspirate, dispense, etc.).
- Document everything in `docs/PROTOCOL_NOTES.md`.
- Tool: `tools/replay_trace.py` for hypothesis testing.

### Phase 4 — Driver implementation

- Implement `protocol.py` encode/decode functions.
- Implement `driver.py` command methods.
- Expand test suite with real packet fixtures.
- Validate against live hardware.

## Dependency rules

```
driver.py  →  safety.py
driver.py  →  protocol.py  →  (no further internal deps)
driver.py  →  serial_link.py  →  pyserial
```

`protocol.py` must **never** import `driver` or `safety`.
`serial_link.py` must **never** import `protocol` or `driver`.
