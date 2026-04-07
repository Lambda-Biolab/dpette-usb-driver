# Contributing to dpette-usb-driver

## Project overview

This is a reverse-engineered driver for DLAB dPette electronic pipettes.
The protocol was decoded through 48 live hardware experiments and a
PetteCali serial capture.  See `docs/EXPERIMENT_LOG.md` for the full
history.

## Development setup

```bash
git clone https://github.com/Lambda-Biolab/dpette-usb-driver.git
cd dpette-usb-driver
python -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
```

## Running tests

```bash
make test    # pytest (no hardware needed)
make lint    # ruff + mypy
make all     # both
```

All tests use mock serial ports — you don't need a pipette connected.

## Code structure

```
src/dpette/
  protocol.py      — packet encode/decode (the protocol bible)
  driver.py        — high-level API (connect, aspirate, dispense)
  serial_link.py   — thin pyserial wrapper
  config.py        — serial port config and discovery
  safety.py        — parameter validation

examples/          — usage examples (start here)
tools/             — reusable CLI scripts for hardware probing
tools/archive/     — one-off experiment scripts (historical reference)
docs/              — protocol spec, experiment log, hardware notes
```

## How to run experiments

When probing the device with new commands, follow this pattern:

1. **Create an interactive script** in `tools/` with logging:
   ```python
   LOGFILE = "captures/live_log.txt"
   _log = open(LOGFILE, "w")
   def log(msg): print(msg); _log.write(msg + "\n"); _log.flush()
   def log_input(prompt): ...  # print + log + input
   ```

2. **Run from the terminal** (not automated) so you can observe the
   pipette's physical response between commands.

3. **Document results** in `docs/EXPERIMENT_LOG.md` with:
   - Experiment number (EXP-NNN)
   - Hypothesis
   - Commands sent and responses received
   - Physical observations (motor, display, sounds)
   - Conclusion

4. **Commit with the experiment number** in the message.

## Protocol reference

All packets are 6 bytes: `[0xFE] [CMD] [B2] [B3] [B4] [CHECKSUM]`

See `docs/PROTOCOL_NOTES.md` for the complete command reference.

### Dangerous commands

**DO NOT send `FE A5 01 00 00 A6`** (enter calibration mode via serial).
This causes persistent Err4 that survives reboots and cannot be cleared
via serial.  See `docs/SAFETY_MODEL.md` and GitHub issue #2.

## Hardware modification

Full volume control requires a BSS138 MOSFET wired across the pipette's
button contacts.  See GitHub issue #3 for the wiring guide and BOM.

## Pull requests

- Run `make all` before submitting
- Add tests for new protocol functions
- Document any new experiments in `EXPERIMENT_LOG.md`
- Don't send dangerous commands to untested devices
