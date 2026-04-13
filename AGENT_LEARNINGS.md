# Agent Learnings

Recurring patterns, gotchas, and solutions discovered during development.

## Format

Each entry follows: **Context** / **Problem** / **Solution**

---

### 1. A5 calibration mode causes persistent Err4

- **Context:** Sending command `A5` with `b2=1` to enter calibration mode
- **Problem:** Sets a persistent flag in the pipette firmware that causes
  Err4 on every subsequent power-on. Cannot be cleared via serial commands.
  Confirmed on two separate devices.
- **Solution:** Never send `A5 b2=1`. The driver uses only `A5 b2=0` for
  handshake. Clearing Err4 requires PetteCali (Windows software) with a
  full calibration cycle.

### 2. B3 KEY produces double response

- **Context:** Sending B3 (aspirate/dispense) commands
- **Problem:** The device sends two response packets for every B3 command.
  Reading only one response desynchronizes the serial buffer, causing
  subsequent reads to return stale data.
- **Solution:** Always read two responses after B3. See
  `protocol.py` and `driver.py` implementation.

### 3. DI mode blow does not trigger motor on basic dPette

- **Context:** Using dilution (DI) mode on the basic dPette (not dPette+)
- **Problem:** B3 blow command in DI mode does not drive the motor, so
  liquid is not expelled.
- **Solution:** Switch to PI mode with `enter_mode(WorkingMode.PI)` which
  homes the motor and expels all liquid. Document this as a known limitation.

### 4. Piston return creates suction after dispense

- **Context:** Dispensing liquid with tip submerged in liquid
- **Problem:** B3 blow includes a piston return to home position. If the
  tip is still in liquid, the return stroke draws extra liquid into the tip.
- **Solution:** Always raise the tip above the liquid surface before
  dispensing. This is a mechanical constraint, not a software bug.

### 5. EEPROM k/b coefficient writes can break motor control

- **Context:** Writing calibration coefficients to EEPROM via A4 command
- **Problem:** Incorrect values cause the motor to refuse aspirate/dispense
  commands with no error response — it simply does nothing.
- **Solution:** `write_ee()` is provisional. Do not write EEPROM values
  without understanding the exact byte layout from PetteCali captures.
