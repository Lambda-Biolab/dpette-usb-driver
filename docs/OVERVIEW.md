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

### Phase 1 — Static analysis (no hardware needed)

- Download PetteCali.exe from DLAB (QR code link).
- Decompile with dnSpyEx or ILSpy (runs on Windows, Wine, or natively).
- Extract: serial port init (baud rate, framing), command strings,
  packet format, checksum algorithm.
- Document findings in `docs/PROTOCOL_NOTES.md`.

### Phase 2 — Discovery

- Connect dPette via USB; confirm it appears as `/dev/tty.SLAB_USBtoUART`.
- Identify VID/PID with `system_profiler` or `cp210x-program`.
- Confirm baud rate from Phase 1 using `tools/scan_baud.py`.

### Phase 3 — Passive capture

- Listen on the serial port while manually operating the pipette
  (button presses for aspirate/dispense) — the MCU may emit status
  bytes or ACKs without the calibration software running.
- Use `tools/dump_raw.py` or SerialTool for logging.
- Optionally: run PetteCali in a Windows VM with USBPcap for full
  bidirectional capture.
- Store captures in `captures/`.

### Phase 4 — Driver implementation

- Implement `protocol.py` encode/decode based on Phase 1 + 3 findings.
- Implement `driver.py` command methods.
- Expand test suite with real packet fixtures.
- Validate against live hardware using `tools/replay_trace.py`.

## Reference projects

| Project | Relevance |
|---------|-----------|
| [ac-rad/digital-pipette-v2](https://github.com/ac-rad/digital-pipette-v2) | DIY pipette with Python serial driver |
| [SerialTool](https://github.com/Duolabs/SerialTool) | Cross-platform serial sniffer (macOS/Linux) |
| [cp210x-program](https://github.com/VCTLabs/cp210x-program) | CP210x EEPROM reader (VID/PID) |
| [dnSpyEx](https://github.com/dnSpyEx/dnSpy) | .NET decompiler/debugger |
| [ILSpy](https://github.com/icsharpcode/ILSpy) | .NET decompiler (multi-platform) |

## Dependency rules

```
driver.py  →  safety.py
driver.py  →  protocol.py  →  (no further internal deps)
driver.py  →  serial_link.py  →  pyserial
```

`protocol.py` must **never** import `driver` or `safety`.
`serial_link.py` must **never** import `protocol` or `driver`.
