# AGENTS.md — dpette-usb-driver

Reverse-engineered Python driver for **DLAB dPette / dPette+** electronic
pipettes. Provides full serial volume control over USB-UART (CP2102) at
9600 baud 8N1. No hardware modifications required for basic operation.

## Architecture

```
src/dpette/
  driver.py        — High-level API (connect, aspirate, dispense, mix, split, dilute)
  protocol.py      — 6-byte packet encode/decode, command enums, working modes
  serial_link.py   — Thin pyserial wrapper (read/write/flush)
  safety.py        — Volume/speed validation, cycle-count limits
  config.py        — SerialConfig dataclass, port discovery
  logging_utils.py — Structured logging helpers
```

## Domain Rules

### Protocol invariants
- All packets are exactly 6 bytes: `[0xFE] [CMD] [B2] [B3] [B4] [CHECKSUM]`
- Checksum = `sum(bytes[1:5]) & 0xFF`
- Volumes are encoded as micro-litres x 100 in 24-bit big-endian
- B3 (KEY) commands produce a **double response** — always read both

### Safety-critical constraints
- **NEVER send `A5 b2=1`** (calibration mode entry) — causes persistent
  Err4 that survives reboots and cannot be cleared via serial
- `driver.py` must only send packets produced by `protocol.encode_packet()`;
  raw hand-crafted bytes are reserved for `tools/` scripts
- Volume and speed parameters pass through `safety.validate_volume()` and
  `safety.validate_speed()` before transmission
- Cycle counter (`MAX_CONTIGUOUS_CYCLES = 50`) prevents unattended runaway

### DI mode workaround
B3 blow does not trigger the motor on basic dPette in dilution mode.
Workaround: call `enter_mode(WorkingMode.PI)` which homes the motor and
expels liquid.

### Piston return suction
B3 blow includes a piston return to home position. If the tip is submerged,
this draws extra liquid. Always dispense with tip above liquid surface.

### EEPROM writes
Writing incorrect calibration values (k/b coefficients) via `A4` can break
motor control. `write_ee()` is provisional — do not use without understanding
the exact byte layout.

## Testing

All tests use **mock serial ports** (pytest-mock). No physical hardware
required for the default test suite.

```bash
make test              # pytest (hardware tests excluded)
make validate          # full read-only gate (format + lint + mypy + tests)
make quick_validate    # fast gate (lint + mypy, no tests)
make lint_fix          # auto-fix formatting and lint issues
make check_complexity  # complexipy analysis
make check_links       # lychee link checker
make check_docs        # markdownlint
```

Tests requiring a physical device use `@pytest.mark.hardware` and run with:
```bash
pytest -m hardware
```

## Experiments

Hardware probing follows a structured process documented in
`docs/EXPERIMENT_LOG.md`. New experiments go in `tools/` with logging to
`captures/`. Archive one-off scripts to `tools/archive/`.

## Key Files

| File | Purpose |
|------|---------|
| [README.md](README.md) | Project overview, quickstart, protocol summary |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup, code structure, experiment workflow |
| [AGENT_LEARNINGS.md](AGENT_LEARNINGS.md) | Gotchas and lessons learned |
| [docs/PROTOCOL_NOTES.md](docs/PROTOCOL_NOTES.md) | Full command reference |
| [docs/SAFETY_MODEL.md](docs/SAFETY_MODEL.md) | Risk analysis and software guardrails |
| [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md) | 55 hardware experiments with results |
| [docs/HARDWARE.md](docs/HARDWARE.md) | CP2102 connection details |
