---
title: "System overview"
status: "DRAFT"
updated: "2026-04-06"
owner: "lambda biolab"
---

# System overview

## Physical architecture

```text
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
             │ UART (TX/RX, 9600 8N1)
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

## How this was built

The protocol was decoded in four overlapping passes:

1. **Static analysis** — Ghidra decompilation of `PetteCali.exe` (the
   official DLAB Windows calibration app — native C++/Qt6, MinGW x86-64).
   Extracted serial init, packet format, and checksum algorithm.
2. **Discovery** — confirmed the dPette enumerates as a Silicon Labs
   CP2102 USB-UART bridge (VID `0x10C4`, PID `0xEA60`), appearing as
   `/dev/cu.usbserial-0001` on macOS or `/dev/ttyUSB0` on Linux. Baud
   rate confirmed against Phase 1 findings.
3. **Live probing** — 55 hardware experiments documented in
   `EXPERIMENT_LOG.md`. Bidirectional capture via PetteCali in a Windows
   VM filled the remaining gaps.
4. **Driver implementation** — `protocol.py` encode/decode, `driver.py`
   command surface, test suite against mocked serial fixtures, then
   validation on live hardware.

## Reference projects

| Project | Relevance |
|---------|-----------|
| [ac-rad/digital-pipette](https://github.com/ac-rad/digital-pipette) | DIY pipette with Python serial driver |
| [SerialTool](https://github.com/Duolabs/SerialTool) | Cross-platform serial sniffer (macOS/Linux) |
| [cp210x-program](https://github.com/VCTLabs/cp210x-program) | CP210x EEPROM reader (VID/PID) |
| [Ghidra](https://ghidra-sre.org/) | Native-binary decompiler used on PetteCali.exe |

## Dependency rules

```text
driver.py  →  safety.py
driver.py  →  protocol.py  →  (no further internal deps)
driver.py  →  serial_link.py  →  pyserial
```

`protocol.py` must **never** import `driver` or `safety`.
`serial_link.py` must **never** import `protocol` or `driver`.
