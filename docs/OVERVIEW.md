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

## Boundary failure-policy

Every I/O or external boundary in `src/dpette/` is pinned to exactly one of
three policies:

- **fail-loud** — raise immediately; failure is a programmer / hardware /
  config problem that silent degradation would hide.
- **wrap-degrade** — catch a specific exception, log a warning, return a
  degraded result.
- **wrap-continue** — wrap-degrade inside a loop; per-item failure must
  not abort the batch.

| Boundary | Location | Policy | Notes |
|---|---|---|---|
| Serial port open | `serial_link.SerialLink.open` | fail-loud | `SerialException` propagates — no port means no link; silent continuation would deceive the caller. |
| Serial write / flush | `serial_link.SerialLink.write` | fail-loud | Unacknowledged writes mean a command was never sent; swallowing skips a pipetting step. |
| Serial read (short) | `serial_link.SerialLink.read` | fail-loud | Returns the short bytes; caller (`_transact`) checks length and raises `TimeoutError`. |
| KEY completion read timeout | `driver._key_command` | **fail-loud (change needed)** | Currently logs a warning and returns the ACK packet as if the motion completed; that masks an unknown motor state. PR δ. |
| Volume / speed validation | `safety.validate_volume`, `safety.validate_speed` | fail-loud | Raises `SafetyError` on out-of-range input. Silent clamping would deliver the wrong volume. |
| Packet encode — byte overflow | `protocol.encode_packet` | **fail-loud (change needed)** | Currently truncates byte values >255 silently; an oversized integer becomes an unintended command byte. PR δ. |
| Packet decode — wrong length / header | `protocol.decode_packet` | fail-loud | Raises `ValueError`; malformed frames indicate noise or protocol mismatch. |
| Packet decode — checksum mismatch | `protocol.decode_packet` | fail-loud | Raises `ValueError`; bad checksum means the bytes can't confirm any motion. |
| Transact timeout | `driver._transact` | fail-loud | Raises `TimeoutError` when fewer than 6 bytes are received. |
| `connect()` exception catch-all | `driver.DPetteDriver.connect` | wrap-degrade | Catches `OSError` / `TimeoutError` / `RuntimeError`, enters stub mode for CI/simulation. A `strict=True` opt-out for lab callers is tracked alongside PR δ. |
| Cycle-count overrun | `driver._check_cycle_limit` | fail-loud | Raises `RuntimeError` after `MAX_CONTIGUOUS_CYCLES` (50) — cumulative mechanical abuse must not be ignorable. |
| Log file handler creation | `logging_utils.get_logger` | **wrap-degrade (change needed)** | Currently lets `OSError` propagate if the log dir is unwritable; should fall back to console-only logging. PR δ. |
| Port discovery returns `None` | `config.guess_default_port` (at call sites) | fail-loud at call site | The function is intentionally nullable; callers must assert non-None with a readable message before passing it to `SerialConfig`. |

The three rows tagged *(change needed)* describe known gaps tracked in
a separate PR; everything else matches the recommended policy today.
