---
title: "dpette-usb-driver"
status: "DRAFT"
updated: "2026-04-06"
owner: "lambda biolab"
---

# dpette-usb-driver

Reverse-engineered USB/serial driver for **DLAB dPette** and **dPette+** electronic pipettes.

These pipettes use a Silicon Labs **CP210x** USB-UART bridge to communicate
with DLAB's proprietary Windows calibration software.  This project captures
that serial traffic, reverse-engineers the protocol, and provides an
open-source Python driver for programmatic pipette control on Linux and macOS.

## Architecture

```
┌────────────┐   USB    ┌────────┐   UART   ┌─────┐   motor   ┌────────┐
│  Host PC   │ ──────── │ CP210x │ ──────── │ MCU │ ────────── │ Piston │
│ (this code)│          │ bridge │          │     │            │        │
└────────────┘          └────────┘          └─────┘            └────────┘
```

**Phases:**

1. **Discovery** — identify baud rate, framing, and handshake (`tools/scan_baud.py`)
2. **Capture** — record USB traffic from the vendor software (`tools/capture_usb.py`)
3. **Analysis** — decode packets, document in `docs/PROTOCOL_NOTES.md`
4. **Driver** — implement `dpette.driver.DPetteDriver` as protocol becomes known

## Safety & warranty disclaimer

> **WARNING:** This software is provided as-is for research and educational
> purposes.  Using it may void your pipette's warranty.  The authors are not
> responsible for damage to hardware, incorrect pipetting results, or any
> downstream consequences.
>
> The driver enforces software safety limits (see `docs/SAFETY_MODEL.md`),
> but these cannot protect against all failure modes.  Never use this
> software for clinical or safety-critical applications without independent
> validation.
>
> This project does **not** flash firmware or execute code on the pipette.

## Quickstart

```bash
# Clone and set up
git clone <repo-url> && cd dpette-usb-driver
make init

# List serial ports (Linux)
python -c "import serial.tools.list_ports; [print(p) for p in serial.tools.list_ports.comports()]"

# Scan for the pipette's baud rate
python tools/scan_baud.py --port /dev/ttyUSB0

# Dump raw traffic
python tools/dump_raw.py --port /dev/ttyUSB0 --baud 9600
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
  protocol.py      — frame encoding / decoding (no I/O)
  safety.py        — parameter validation and mechanical limits
  driver.py        — high-level pipetting API
  logging_utils.py — centralised logging

tools/             — standalone CLI scripts for capture and analysis
tests/             — pytest suite (works without hardware)
captures/          — .pcap and raw binary captures (gitignored except .gitkeep)
docs/              — protocol notes, hardware info, safety model
```

## License

MIT — see [LICENSE](LICENSE).
