---
title: "Protocol notes"
status: "DRAFT"
updated: "2026-04-06"
owner: "lambda biolab"
---

# Protocol notes

Document all findings here **before** implementing them in code.

## Source strategy

Primary source: decompile PetteCali.exe (likely .NET WinForms) with
dnSpyEx or ILSpy to extract the complete protocol without hardware
interaction.  Secondary: passive serial capture on macOS while manually
operating the pipette.

## Findings from PetteCali instructions PDF

Source: `captures/static-analysis/pettecali_instructions.pdf`
(DLAB Electronic Pipette Calibration Software operating Instructions)

### Software metadata

- **Application name:** dPetteCalibrate
- **Version:** v1.0.0
- **Copyright:** 2024 DLAB Scientific Co.,Ltd
- **Framework:** almost certainly .NET WinForms (UI style, Chinese lab
  instrument era, 360 antivirus whitelist instruction)
- **Platform:** Windows only (separate installers for Win7 and Win10/11)

### Known commands (inferred from UI error/success messages)

| Command    | Evidence                                          | Purpose                        |
|------------|---------------------------------------------------|--------------------------------|
| HandShake  | "HandShake TimeOut!" error dialog (page 11)       | Initial connection handshake   |
| ReadE      | "ReadE TimeOut" error when device sleeping (p.11) | Read EEPROM / calibration data |
| WriteE     | "WriteE Succeed" success dialog (page 8)          | Write calibration coefficients |

"ReadE" and "WriteE" strongly suggest EEPROM read/write operations — the
software reads existing calibration from the pipette's non-volatile memory
and writes new coefficients after calibration.

### Calibration model

The dPette uses a **linear calibration model** with two coefficients:

- **k** — slope (gain)
- **b** — offset (intercept)

Relationship (assumed): `actual_volume = k * motor_steps + b` or similar.

Observed values from screenshots:

| Context         | k      | b      | Source  |
|-----------------|--------|--------|---------|
| After calibration | 1.2253 | 1.7448 | page 7  |
| Factory reset   | 1.2742 | 6.8078 | page 9  |

The "Restore Factory Settings" workflow requires the user to contact
DLAB after-sales to get the factory k/b values for their specific device.

### Calibration workflow

1. Select dPette type (dropdown: "dPette", likely also "dPette+")
2. Select volume range (dropdown: "0.5-10", and presumably others)
3. Select COM port
4. Click "Connect" → triggers HandShake
5. 3-step calibration, each at a different volume point:
   - Step 1: 100 µL (5 measurements)
   - Step 2: 500 µL (5 measurements)
   - Step 3: 1000 µL (5 measurements)
6. At each step, user manually enters balance readings
7. Software computes average, precision (CV%), accuracy (%)
8. Pass/fail thresholds vary by volume:
   - 100 µL: precision ≤ 3.00%, accuracy ≤ 5.00%
   - 1000 µL: precision ≤ 0.50%, accuracy ≤ 1.00%
9. If all 3 steps pass → compute k and b → "WriteData" button
10. WriteE sends coefficients to device EEPROM
11. Device must be restarted after successful write

### Connection requirements

- Device must be **awake** (not in standby) before connecting
- Press the operation button to wake the pipette
- Standby state: screen off or dim (page 11 photo)
- Connectable state: screen showing volume/mode info (page 12 photo)
- Connection failure modes:
  - Cable not connected / port occupied → connection error
  - Device in standby → "ReadE TimeOut"
  - Device not responding to handshake → "HandShake TimeOut"

## Serial parameters

| Parameter  | Value       | Source / confidence          |
|------------|-------------|------------------------------|
| Baud rate  | unknown     | need exe decompile or probe  |
| Byte size  | 8 (assumed) | —                            |
| Parity     | N (assumed) | —                            |
| Stop bits  | 1 (assumed) | —                            |
| Bridge     | CP210x      | confirmed (PDF page 2)       |

## Framing

- Start byte(s): ?
- Length field: ?
- Message type byte: ?
- Payload: ?
- Checksum / CRC: ?
- End byte(s): ?

## Commands (host → device)

| Name       | Type byte | Payload format | Description              |
|------------|-----------|----------------|--------------------------|
| HANDSHAKE  | ?         | ?              | Initial connection probe |
| READ_E     | ?         | —              | Read EEPROM (cal data)   |
| WRITE_E    | ?         | k, b floats?   | Write calibration coeffs |
| PING       | ?         | —              | Liveness check (if any)  |

## Responses (device → host)

| Name       | Type byte | Payload format     | Description               |
|------------|-----------|--------------------|---------------------------|
| ACK        | ?         | —                  | Command accepted          |
| CAL_DATA   | ?         | k, b floats?       | Current calibration data  |
| ERROR      | ?         | ?                  | Error code                |
| IDENTITY   | ?         | model, range, etc? | Device identification     |

## Checksums

Algorithm: unknown (candidates: XOR, CRC-8, CRC-16, modular sum)

## Capture examples

<!-- Paste annotated hex dumps here as they are captured -->

```
# No captures yet — awaiting either:
# 1. Decompilation of PetteCali.exe
# 2. Live passive capture with scan_baud.py / dump_raw.py
```

## Next steps

1. **Get PetteCali.exe** — download via WeiyunCloud (needs WeChat/QQ
   account) or request from DLAB support / distributor
2. **Decompile** — `ilspycmd -p -o ./decompiled PetteCali.exe` to
   extract serial init code (baud rate) and command packet format
3. **Passive capture** — connect dPette on macOS, run `scan_baud.py`
   to find baud rate, then `dump_raw.py` while pressing buttons
4. **Confirm and implement** — update this file, then implement in
   `protocol.py` and `driver.py`
