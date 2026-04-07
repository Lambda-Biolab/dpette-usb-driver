---
title: "dpette-usb-driver"
status: "ACTIVE"
updated: "2026-04-07"
owner: "lambda biolab"
---

# dpette-usb-driver

Reverse-engineered USB/serial driver for **DLAB dPette** and **dPette+** electronic pipettes.

These pipettes use a Silicon Labs **CP2102** USB-UART bridge (VID `0x10C4`,
PID `0xEA60`) to communicate at 9600 baud 8N1.  This project provides an
open-source Python driver for programmatic pipette control on Linux and macOS.

## What works today (v0.1.0)

- **Aspirate** at the physical dial volume (B0 prime → B3 aspirate)
- **Dispense** (B0 command)
- **EEPROM read/write** of calibration coefficients
- **Volume control** via A6 + physical button press in calibration mode
- Full 6-byte protocol decoded (48 experiments, PetteCali serial capture)
- 56 tests passing, complete documentation

## Architecture

```
┌────────────┐   USB    ┌────────┐   UART    ┌─────┐   motor   ┌────────┐
│  Host PC   │ ──────── │ CP2102 │ ──────── │ MCU │ ────────── │ Piston │
│ (this code)│          │ bridge │          │     │            │        │
└────────────┘          └────────┘          └─────┘            └────────┘
```

### With button MOSFET (roadmap):

```
┌────────────┐   USB    ┌────────┐   UART    ┌─────┐   motor   ┌────────┐
│  Host PC   │ ──────── │ CP2102 │ ──────── │ MCU │ ────────── │ Piston │
│ (this code)│          │ bridge │          │     │            │        │
└──────┬─────┘          └────────┘          └──┬──┘            └────────┘
       │ GPIO                                  │
       ▼                                       │
  ┌─────────┐   BSS138    ┌────────┐           │
  │ RP2040  │ ──────────▶ │ Button │ ──────────┘
  │         │   MOSFET    │contacts│  (simulates button press)
  └─────────┘             └────────┘
```

## Confirmed automation cycle (EXP-048)

With a BSS138 MOSFET wired across the pipette's button contacts:

```
Enter cal mode (once) →
  A6 set volume (serial)  →  button press (MOSFET)  →  B0 dispense (serial)
  A6 new volume (serial)  →  button press (MOSFET)  →  B0 dispense (serial)
  ... repeat at any volume
```

Tested at 30, 100, and 300 µL — volumes match A6 setting exactly.

## Roadmap

### v0.1.0 — Protocol & fixed-volume pipetting ✅
- [x] 6-byte protocol fully decoded
- [x] Handshake, aspirate (B3), dispense (B0)
- [x] EEPROM read/write (A3/A4)
- [x] PetteCali serial capture analysis
- [x] 48 experiments documented

### v0.2.0 — Button press hardware (current)
- [ ] BSS138 MOSFET wired across button contacts
- [ ] RP2040 or Arduino GPIO to drive MOSFET
- [ ] `driver.trigger_button()` method via GPIO
- [ ] Full A6 → MOSFET → B0 automation cycle
- [ ] Test on fresh dPette (avoid Err4 from serial A5 b2=1)

### v0.3.0 — Calibration & error handling
- [ ] Proper recalibration via PetteCali (fix dummy k/b values)
- [ ] Err4 investigation via debug port (open device, identify MCU)
- [ ] Err4 prevention (enter cal mode via MOSFET, not serial A5 b2=1)
- [ ] Automated error recovery

### v0.4.0 — Lab integration
- [ ] Multi-pipette support (multiple serial ports)
- [ ] Protocol automation scripts (serial dilutions, plate filling)
- [ ] Integration with lab automation frameworks (OpenTrons, PyLabRobot)
- [ ] Volume accuracy validation with gravimetric testing

## Safety & warranty disclaimer

> **WARNING:** This software is provided as-is for research and educational
> purposes.  Using it may void your pipette's warranty.  The authors are not
> responsible for damage to hardware, incorrect pipetting results, or any
> downstream consequences.
>
> **DANGEROUS COMMANDS:** Sending `FE A5 01` (enter calibration mode) via
> serial causes persistent Err4 that survives reboots.  See
> `docs/PROTOCOL_NOTES.md` for details.  The driver does not send this
> command — use the MOSFET button press to enter cal mode instead.
>
> The driver enforces software safety limits (see `docs/SAFETY_MODEL.md`),
> but these cannot protect against all failure modes.  Never use this
> software for clinical or safety-critical applications without independent
> validation.

## Quickstart

```bash
# Clone and set up
git clone https://github.com/Lambda-Biolab/dpette-usb-driver.git
cd dpette-usb-driver
make init

# Connect pipette via USB
# On macOS: /dev/cu.usbserial-0001
# On Linux: /dev/ttyUSB0

# Run tests (no hardware needed)
make test
```

## Development

```bash
make lint    # ruff + mypy
make test    # pytest
make all     # both
```

## Project structure

```
src/dpette/
  config.py        — serial port configuration and discovery
  serial_link.py   — thin pyserial wrapper (raw I/O only)
  protocol.py      — frame encoding / decoding (confirmed from 48 experiments)
  safety.py        — parameter validation and mechanical limits
  driver.py        — high-level pipetting API
  logging_utils.py — centralised logging

tools/             — 40+ exploratory scripts from RE session
tests/             — pytest suite (56 tests, works without hardware)
docs/
  PROTOCOL_NOTES.md  — full protocol specification
  EXPERIMENT_LOG.md  — 48 experiments with results and dead ends
  HARDWARE.md        — CP2102 details, device identification
  SAFETY_MODEL.md    — mechanical risks and software guardrails
```

## Key documentation

- [Protocol Notes](docs/PROTOCOL_NOTES.md) — complete packet format, command reference
- [Experiment Log](docs/EXPERIMENT_LOG.md) — 48 experiments, chronological
- [Hardware Notes](docs/HARDWARE.md) — CP2102, MCU, device connection
- [Safety Model](docs/SAFETY_MODEL.md) — risks, limits, dangerous commands

## License

MIT — see [LICENSE](LICENSE).
