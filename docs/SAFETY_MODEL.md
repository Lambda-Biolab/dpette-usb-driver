---
title: "Safety model"
status: "DRAFT"
updated: "2026-04-06"
owner: "lambda biolab"
---

# Safety model

## Mechanical risks

### 1. Piston overtravel

If the piston is driven beyond its mechanical endpoints, it can damage
the seals, bend internal components, or jam.

**Mitigation:** `safety.validate_volume()` rejects volumes outside the
calibrated range for the connected model.

### 2. Motor stall

Sending rapid or conflicting commands may stall the stepper motor,
causing missed steps, position drift, or overheating.

**Mitigation:** commands are serialised through `DPetteDriver`; a
contiguous-cycle counter (`MAX_CONTIGUOUS_CYCLES = 50`) forces a pause
so the operator can inspect the device.

### 3. Uncontrolled tip ejection

Ejecting a tip while liquid is present could spray hazardous material.

**Mitigation:** (future) sequence checks — warn or block `eject_tip()`
if the last operation was `aspirate()` without a corresponding `dispense()`.

### 4. Unknown command side-effects

Sending arbitrary bytes to the pipette could trigger undocumented
factory or debug modes.

**Mitigation:** production code must only send packets produced by
`protocol.encode_packet()`.  Direct `serial_link.write()` calls with
hand-crafted bytes are reserved for `tools/` scripts used during
reverse-engineering.

### 5. Calibration mode entry causes persistent Err4

Sending `A5 b2=1` (enter calibration mode) sets a persistent flag
that causes Err4 on every subsequent reboot.  This was confirmed on
two separate devices and **has never been cleared** by any known
method, including a full calibration through PetteCali (Windows
software) and its ResetFactory command.

**Mitigation:** the driver NEVER sends `A5 b2=1`.  The `connect()`
method uses only `A5 b2=0` (handshake) and `B0 b2=1` (prime).
The `Command.HANDSHAKE` with `b2=1` is intentionally not exposed
as a high-level method.

### 6. EEPROM writes can break motor control

Writing incorrect calibration values (k/b coefficients) to EEPROM
via `A4` can cause the motor to refuse aspirate/dispense commands.

**Mitigation:** `write_ee()` is marked as provisional and should not
be used without understanding the exact byte layout.

## Safety invariants

1. **Volume bounds** — every `set_volume()` call passes through
   `safety.validate_volume()`.
2. **Speed bounds** — every speed parameter passes through
   `safety.validate_speed()`.
3. **Cycle limit** — `aspirate()` and `dispense()` increment a counter;
   after `MAX_CONTIGUOUS_CYCLES` (50), the driver refuses further
   commands until `reset_cycle_count()` is called.
4. **Connection required** — all command methods check `_require_connected()`
   before any I/O.
5. **Encode-only transmission** — `driver.py` sends only the output of
   `protocol.encode_packet()`, never raw hand-crafted bytes.

## Limits dataclass

```python
class SafetyLimits(NamedTuple):
    max_volume_ul: float    # model-dependent
    max_cycles: int         # default 50
    max_speed_level: int    # model-dependent
```

Default values are intentionally conservative.  Tighten or relax them
per model once real calibration data is available.

## What this does NOT protect against

- Physical misuse (wrong tips, contaminated reagents).
- Electrical faults (USB cable damage, power brownouts).
- Firmware bugs in the pipette's own MCU.
- Concurrent access from multiple processes.

This safety model is a best-effort software layer, not a substitute
for operator training and common sense.
