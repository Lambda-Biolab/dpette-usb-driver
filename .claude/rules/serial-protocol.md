# Serial Protocol Safety

## Packet format
All packets are exactly 6 bytes: `[0xFE] [CMD] [B2] [B3] [B4] [CHECKSUM]`

## Critical constraints
- **NEVER send `A5 b2=1`** (calibration mode entry) — causes persistent Err4
  that survives reboots and cannot be cleared via serial
- Only send packets produced by `protocol.encode_packet()`; raw hand-crafted
  bytes are reserved for `tools/` scripts
- Volume and speed parameters MUST pass through `safety.validate_volume()` and
  `safety.validate_speed()` before transmission

## EEPROM writes
Writing incorrect calibration values (k/b coefficients) via `A4` can break
motor control. `write_ee()` is provisional — do not use without understanding
the exact byte layout.
