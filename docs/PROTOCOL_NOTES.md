---
title: "Protocol notes"
status: "ACTIVE"
updated: "2026-04-06"
owner: "lambda biolab"
---

# Protocol notes

## Source strategy

Primary source: Ghidra decompilation of PetteCali.exe (native C++/Qt6,
MinGW x86-64).  Secondary: DLAB calibration instructions PDF.  Tertiary:
live probing against real hardware (CP2102 on macOS).

Full decompilation: `captures/static-analysis/decompiled_all.c` (1497 functions).
Actual application binary: `captures/static-analysis/extracted/app/PetteCali.exe`.

## Serial parameters (CONFIRMED — live hardware)

| Parameter    | Value   | Source                                |
|--------------|---------|---------------------------------------|
| Baud rate    | 9600    | `setBaudRate(0x2580)` + live verified |
| Data bits    | 8       | `setDataBits(8)` + live verified      |
| Stop bits    | 1       | `setStopBits(1)` + live verified      |
| Parity       | None    | `setParity(0)` + live verified        |
| Flow control | None    | `setFlowControl(0)` + live verified   |
| Bridge chip  | CP2102  | `system_profiler` on macOS            |
| VID          | 0x10C4  | Silicon Labs (confirmed)              |
| PID          | 0xEA60  | CP2102 USB to UART (confirmed)        |
| Device node  | `/dev/cu.usbserial-0001` | macOS (Apple Silicon)    |

## Packet format (CONFIRMED — disassembly + live)

All packets are **6 bytes**:

```
[HEADER] [CMD] [B2] [B3] [B4] [CHECKSUM]
 1 byte  1 byte 1    1    1     1 byte
```

**Header bytes:**
- Host → device: `0xFE`
- Device → host: `0xFD`

**Checksum:** simple byte sum of bytes[1] through bytes[4] (4 bytes),
truncated to 8 bits.  Confirmed by: (a) disassembly of checksum loop
in FUN_140069730, (b) live verification — bad checksums get no response.

Source: instruction-level disassembly of `PetteCali.exe` at addresses
0x140069730 (WriteEE), 0x140069a10 (SendCaliVolume), 0x140069c60
(HandShake/StartCalibrate).

### Important: NOT 7 bytes

The initial Ghidra decompilation suggested 7-byte packets with separate
ADDR_HI/ADDR_LO/VAL_HI/VAL_LO fields.  This was WRONG — Ghidra's
decompiler output was misleading due to Qt QByteArray call obfuscation.
Instruction-level disassembly confirmed 6-byte packets with 3 payload
bytes (B2, B3, B4) between CMD and CHECKSUM.

## Commands (CONFIRMED — disassembly + live)

| CMD byte | Name             | Function in binary | Direction | Confirmed |
|----------|------------------|--------------------|-----------|-----------|
| `0xA0`   | **HELLO**        | —                  | host→dev  | **live ✓ EXP-049** |
| `0xA1`   | INFO             | —                  | host→dev  | live ✓    |
| `0xA2`   | STA              | —                  | host→dev  | live ✓    |
| `0xA3`   | EE_READ          | response handler   | host→dev  | live ✓    |
| `0xA4`   | EE_WRITE         | FUN_140069730      | host→dev  | live ✓    |
| `0xA5`   | DEMARCATE        | FUN_140069c60      | host→dev  | live ✓ (cal mode) |
| `0xA6`   | DMRCT_VOLUM      | FUN_140069a10      | host→dev  | live ✓ (cal only) |
| `0xA7`   | RESET            | —                  | host→dev  | live ✓    |
| `0xA8`   | DMRCT_PULSE      | —                  | host→dev  | live ✓    |
| **`0xB0`** | **WOL (mode)** | —                  | host→dev  | **live ✓ EXP-049** |
| **`0xB1`** | **SPEED**      | —                  | host→dev  | **live ✓ EXP-049** |
| **`0xB2`** | **PI_VOLUM**   | —                  | host→dev  | **live ✓ EXP-050 motor** |
| **`0xB3`** | **KEY (suck/blow)** | —             | host→dev  | **live ✓ EXP-050 motor** |
| `0xB4`   | ST_VOLUM         | —                  | host→dev  | live ✓    |
| `0xB5`   | ST_NUM           | —                  | host→dev  | live ✓    |
| `0xB6`   | DI1_VOLUM        | —                  | host→dev  | live ✓    |
| `0xB7`   | DI2_VOLUM        | —                  | host→dev  | live ✓    |

CMD bytes extracted from `mov edx, 0xffffffXX` instructions immediately
before `call rbx` (QByteArray::append) in each packet-builder function.

### Command details

**HandShake / StartCalibrate (0xA5):**

```
TX: [FE] [A5] [param] [00] [00] [cksum]
RX: [FD] [A5] [00]    [00] [00] [A5]
```

- `param=0`: connection handshake / exit calibration mode (confirmed live)
- `param=1`: enter calibration mode — causes persistent Err4 on the
  pipette display.  Does NOT trigger motor movement by itself.
- Response is always `fd a5 00 00 00 a5` regardless of param value
- **WARNING:** A5 b2=1 causes persistent Err4 that survives reboots.
  Confirmed on two separate devices.  Only use when necessary.
- Source: FUN_140069c60 disassembly; `param` comes from `movsx edx, sil`
  at 0x140069ce1

**SendCaliVolume (0xA6):**

```
TX: [FE] [A6] [vol_hi] [vol_lo] [00] [cksum]
RX: [FD] [A6] [00]     [00]     [00] [A6]
```

- Volume encoded as `volume_µL × 10`, big-endian in bytes[2:3]
- Example: 200 µL → 2000 = 0x07D0 → `[FE A6 07 D0 00 7D]`
- **In cal mode**: changes the display volume (confirmed live — display
  updated from 100 to 50, 150, 200 etc.)
- **Does NOT control motor travel** — tested: A6=10 and A6=100 both
  aspirated the same amount.  Volume is set by physical dial only.
- Source: FUN_140069a10 disassembly; calling code at line 12254
  shows `iVar3 = param_2 * 10`

**WriteEE (0xA4) — CONFIRMED from PetteCali capture:**

```
TX: [FE] [A4] [00] [ADDR] [VALUE] [cksum]
RX: [FD] [A4] [??] [00]   [00]   [cksum]
```

- **Address in byte[3], value in byte[4]** (confirmed from serial capture)
- Byte[2] is always 0x00 in observed writes
- PetteCali sends each write twice (retry pattern)
- Source: serial capture of PetteCali WriteData session (EXP-031)

**ReadEE (0xA3) — CONFIRMED from PetteCali capture:**

```
TX: [FE] [A3] [00] [ADDR] [00] [cksum]
RX: [FD] [A3] [VALUE] [00] [00] [cksum]
```

- **Address in byte[3]** (NOT byte[2] — this is why earlier reads failed)
- Byte[2] of TX is always 0x00
- Response byte[2] contains the EEPROM value
- PetteCali reads addresses 0x80 through 0xAD sequentially, each twice
- Source: serial capture of PetteCali calibration session (EXP-031)

**Aspirate (0xB3) — CONFIRMED live, motor movement:**

```
TX: [FE] [B3] [01] [00] [00] [B4]
RX: [FD] [B3] [00] [00] [00] [B3]   ← motor started
    [FD] [B3] [01] [00] [00] [B4]   ← motor finished (12 bytes total)
```

- `b2=0x01` triggers aspiration at the pipette's physical dial volume
- Returns a **double 6-byte response**: first packet (b2=0x00) = started,
  second packet (b2=0x01) = completed
- **REQUIRES B0 b2=1 to be sent first** ("prime") — without the prior
  B0, B3 is rejected (returns single 6-byte response, no motor)
- Rejected in calibration mode
- Confirmed on clean 10-100 µL device with hands completely off pipette

**Dispense / Prime (0xB0) — CONFIRMED live, motor movement:**

```
TX: [FE] [B0] [01] [00] [00] [B1]
RX: [FD] [B0] [00] [00] [00] [B0]
```

- `b2=0x01` triggers dispensing AND serves as the "prime" command
  that enables B3 aspirate to work
- Returns a single 6-byte response (b2=0x00 = acknowledged)
- **Must be sent before B3** — B3 is rejected without a prior B0
- Works in both normal and calibration modes (confirmed live)
- `b2=0x00` does NOT trigger dispense

**Data dump commands (0xA1, 0xA2) — 13-byte responses:**

```
TX: [FE] [A1] [b2] [b3] [b4] [cksum]
RX: [FD] [A1] [00] [00] [00] [00] [00] [00] [00] [00] [00] [00] [A1]
```

- Both return 13-byte responses (header + cmd + 10 data bytes + checksum)
- All data bytes are zero (uncalibrated device)
- Payload (b2/b3/b4) does not affect the response
- Likely bulk calibration data read commands

## Response format (CONFIRMED — live)

All observed device responses are 6 bytes:

```
[0xFD] [CMD_ECHO] [B2] [B3] [B4] [CHECKSUM]
```

- Header is always `0xFD` (vs `0xFE` for host→device)
- CMD byte is echoed from the request (except 0xA8 → echoes 0xA6)
- Checksum follows same algorithm as TX packets
- Invalid checksums in TX → no response at all (confirmed live)
- Invalid/unknown CMD bytes (0xAF, 0x01, 0x03, 0x06) → no response

## EEPROM memory map (from dPette.ini — CONFIRMED addresses)

From `system/CaliEEParam/dPette.ini` (GBK-encoded), translated:

| Address | Len | Name (Chinese)     | Name (English)              | Encoding          |
|---------|-----|--------------------|-----------------------------|--------------------|
| `0x80`  | 2   | 标定点数           | Calibration point count     | integer            |
| `0x82`  | 2   | 标定体积1          | Calibration volume 1        | value × 10         |
| `0x84`  | 2   | 标定体积2          | Calibration volume 2        | value × 10         |
| `0x86`  | 2   | 标定体积3          | Calibration volume 3        | value × 10         |
| `0x88`  | 2   | 标定体积4          | Calibration volume 4        | value × 10         |
| `0x8A`  | 2   | 标定体积5          | Calibration volume 5        | value × 10         |
| `0x8C`  | 2   | 标定体积6          | Calibration volume 6        | value × 10         |
| `0x90`  | 4   | 第一段标定系数k     | Segment 1 coefficient k     | value × 10000      |
| `0x94`  | 4   | 第一段标定系数b     | Segment 1 coefficient b     | value × 10000      |
| `0x98`  | 4   | 第二段标定系数k     | Segment 2 coefficient k     | value × 10000      |
| `0x9C`  | 4   | 第二段标定系数b     | Segment 2 coefficient b     | value × 10000      |
| `0xA0`  | 4   | 出厂默认第一段系数k | Factory default seg1 k      | value × 10000      |
| `0xA4`  | 4   | 出厂默认第一段系数b | Factory default seg1 b      | value × 10000      |
| `0xA8`  | 4   | 出厂默认第二段系数k | Factory default seg2 k      | value × 10000      |
| `0xAC`  | 4   | 出厂默认第二段系数b | Factory default seg2 b      | value × 10000      |

Default values from ini: k=12305 (1.2305), b=110046 (11.0046).

Note: 2-byte params are read as individual bytes (addr, addr+1).
4-byte params are read as 4 individual bytes (addr through addr+3).

### Live EEPROM state

All EEPROM addresses returned zero values when probed (2026-04-06).
This is consistent with an uncalibrated device — factory defaults are
likely stored in firmware, not EEPROM.

Debug strings in the response handler confirm hex addresses match the
ini file (e.g., "addr 87" = 0x87, "addr 93" with label "sk" = segment k).

## Device models and volume ranges

From `system/DeviceList.ini`:

| Type index | Device type |
|------------|-------------|
| 1          | DPETTE      |
| 2          | DPETTE+     |
| 3          | DPETTE+8    |
| 4          | PETTE       |
| 5          | PETTEMULTI  |

Volume ranges per device — see `DeviceList.ini` for full list.
DPETTE supports: 0.5-10, 5-50, 20-200, 30-300, 100-1000 µL.

## Calibration thresholds

Each volume range has 3 calibration points with pass/fail criteria:

- **CVRange** — maximum acceptable coefficient of variation (precision)
- **CaliVolRange** — maximum acceptable deviation from target (accuracy)
- **RetestVolRange** — maximum deviation for retest pass

Example for 100-1000 µL range:

| Point | Volume | CV max | Accuracy max |
|-------|--------|--------|--------------|
| 1     | 100 µL | 2.40%  | ±6           |
| 2     | 500 µL | 0.80%  | ±6           |
| 3     | 1000 µL | 0.80% | ±10          |

## Calibration model

The dPette uses a **piecewise linear calibration model** with per-segment
coefficients:

- **k** — slope (gain), stored as `value × 10000`
- **b** — offset (intercept), stored as `value × 10000`

Relationship: `actual_volume = k * motor_steps + b` (assumed).

Two segments allow different k/b for low-volume and high-volume ranges.

## Data receive handler (from decompilation)

FUN_14001d850 (`readData` slot, connected to `QSerialPort::readyRead`):

1. `QIODevice::readAll()` — gets available bytes
2. Frame assembler: buffers bytes at `param_1 + 0x68` until 6 bytes
3. Checks byte[0] == `0xFD` (response header)
4. Dispatches on byte[1]:
   - `0xA3`: enters calibration data parser (giant flag-based state machine)
   - Other: standard ACK handling
5. For 0xA3: checks flags at `param_1 + 0x80` through `0x8d` to determine
   which EEPROM address was being read, extracts value via FUN_140069e00

FUN_14001af80 (buffered frame parser):
- Same dispatch logic for frames assembled across multiple readyRead calls
- Same flag-based state machine for 0xA3 data

Response timeout: 1000ms per read (`_timerRead->start(1000)`).

## Remote pipetting flow (CONFIRMED — live hardware, 2026-04-06)

### Pipetting sequence (CONFIRMED — hands-off, no Err4)

Tested on clean dPette 10-100 µL.  Set volume on the physical dial,
then control aspirate/dispense remotely.

```
┌─────────────────────────────────────────────────────────┐
│ Prerequisites:                                          │
│   - Set volume on pipette dial/buttons                  │
│   - Dismiss Err4 if showing (hold pipette button)       │
│   - Attach tip                                          │
│                                                         │
│ 1. Handshake         [FE A5 00 00 00 A5]               │
│    → device ACKs     [FD A5 00 00 00 A5]               │
│                                                         │
│ 2. Prime (B0)        [FE B0 01 00 00 B1]               │
│    → device ACKs     [FD B0 00 00 00 B0]               │
│    (REQUIRED before B3 — enables aspirate)              │
│                                                         │
│ 3. Aspirate (B3)     [FE B3 01 00 00 B4]               │
│    → motor started   [FD B3 00 00 00 B3]               │
│    → motor done      [FD B3 01 00 00 B4]  (12 bytes)   │
│                                                         │
│ 4. Dispense (B0)     [FE B0 01 00 00 B1]               │
│    → device ACKs     [FD B0 00 00 00 B0]               │
│                                                         │
│ For next cycle: repeat from step 3 (B0 already primed) │
│ or from step 2 if B3 is rejected.                       │
└─────────────────────────────────────────────────────────┘
```

**Key requirement: B0 must be sent before B3.**  Without the B0 "prime",
B3 returns a single 6-byte response and the motor does not move.  This
was confirmed on a clean device with hands completely off the pipette.

**Volume:** determined by the physical dial setting.  There is no
confirmed way to change the volume remotely via serial commands.

### Remote volume control — CONFIRMED (EXP-050, 2026-04-09)

**Volume control works via the remote control protocol (B2 PI_VOLUM),
NOT the calibration interface (A6).**

The correct sequence is:
```
A0 (handshake) → B0 param=1 (enter PI mode) → B2 vol×100 (set volume)
  → B3 param=1 (aspirate) → B3 param=2 (dispense)
```

B2 encoding: volume in µL × 100, 24-bit big-endian across bytes[2:4].
Example: 200 µL → 20000 → `[FE B2 00 4E 20 20]`

Verified on dPette 30-300 µL with dial at 300: B2=50 drew ~50 µL,
B2=200 drew ~200 µL. Display updated to show B2 volume. Motor travel
matched B2 setting, not the physical dial.

**A6 (calibration volume) does NOT control motor travel** — this remains
true. A6 is for the PetteCali calibration workflow only. B2 is the
correct command for runtime volume control in PI mode.

### DANGEROUS COMMANDS — DO NOT SEND

The following command **permanently damages device state** and should
NOT be sent during normal operation:

```
⚠️  [FE A5 01 00 00 A6]  — Enter Calibration Mode (A5 b2=1)
```

**What it does:** Puts the device into calibration mode and sets a
persistent flag that causes Err4 on every subsequent reboot.

**Confirmed damage:** Sent to two separate dPette devices (30-300 µL
and 10-100 µL).  Both now show Err4 on every power-on.  The error
must be dismissed with the physical button each time.

**How to fix:** Complete a full calibration through PetteCali
(Windows software) and click WriteData.  The physical factory reset
button does NOT clear this flag.  PetteCali's ResetFactory also does
NOT clear it — only WriteData after a complete 3-step calibration.

**Other risky commands:**
- `A4` (WriteEE) — writes to device EEPROM.  Incorrect values can
  affect calibration accuracy.  Our experiments wrote k=1.2313,
  b=0.0000 to the 30-300 device, which may have broken motor control
  until PetteCali recalibration.

Previously documented "cal mode aspirate" findings (EXP-019, EXP-025)
were incorrect — motor movement was caused by physical button presses
during Err4 dismissal, not by serial commands.  These have been
reclassified as dead ends in EXPERIMENT_LOG.md.

## Open questions

1. **WriteEE byte layout** — exact mapping of address and value bytes in
   the 0xA4 packet needs write-then-read confirmation
2. **0xA3 data flow** — how exactly does the device deliver EEPROM data?
   May require a specific command sequence (handshake → start → read)
3. **Err4 prevention** — is there a clean way to enter/exit cal mode
   without triggering Err4?  PetteCali manages this somehow.
4. **Volume readback** — no command was found to read the current volume
   setting from the device
5. **Persistent Err4** — how to clear the startup error without PetteCali

## Next steps

1. **VM serial capture** — run PetteCali in a Windows VM with serial port
   logging to capture the exact enter/exit cal mode sequence (may reveal
   commands that prevent Err4)
2. **Proper recalibration** — use PetteCali with real weight measurements
   to write correct k/b values (the dummy calibration wrote k=1.2313,
   b=0.0000 which may affect accuracy)
3. **Err4 root cause** — deeper analysis of what flag is set and how to
   clear it without PetteCali
