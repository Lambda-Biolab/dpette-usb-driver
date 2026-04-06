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
| `0xA5`   | HandShake        | FUN_140069c60      | host→dev  | live ✓    |
| `0xA6`   | SendCaliVolume   | FUN_140069a10      | host→dev  | live ✓    |
| `0xA4`   | WriteEE          | FUN_140069730      | host→dev  | live ✓    |
| `0xA3`   | (unknown/data?)  | response handler   | host→dev  | live ✓    |
| `0xA7`   | (unknown)        | —                  | host→dev  | live ✓    |
| `0xA0`   | (unknown)        | —                  | host→dev  | live ✓    |
| `0xA1`   | ReadData1        | —                  | host→dev  | live ✓    |
| `0xA2`   | ReadData2        | —                  | host→dev  | live ✓    |
| **`0xB0`** | **Dispense**   | —                  | host→dev  | **live ✓ motor** |
| **`0xB3`** | **Aspirate**   | —                  | host→dev  | **live ✓ motor** |
| `0xB1`   | (unknown flag)   | —                  | host→dev  | live ✓    |
| `0xB2`   | (unknown flag)   | —                  | host→dev  | live ✓    |
| `0xB4`   | (unknown flag)   | —                  | host→dev  | live ✓    |
| `0xB5`   | (unknown flag)   | —                  | host→dev  | live ✓    |
| `0xB6`   | (unknown flag)   | —                  | host→dev  | live ✓    |
| `0xB7`   | (unknown flag)   | —                  | host→dev  | live ✓    |

CMD bytes extracted from `mov edx, 0xffffffXX` instructions immediately
before `call rbx` (QByteArray::append) in each packet-builder function.

### Command details

**HandShake / StartCalibrate (0xA5):**

```
TX: [FE] [A5] [param] [00] [00] [cksum]
RX: [FD] [A5] [00]    [00] [00] [A5]
```

- `param=0`: connection handshake / exit calibration mode (confirmed live)
- `param=1`: enter calibration mode — **triggers aspirate** at the volume
  previously set by A6 (confirmed live with motor movement)
- Response is always `fd a5 00 00 00 a5` regardless of param value
- Entering cal mode (b2=1) shows Err4 on the pipette display; dismiss
  with the physical button to access the calibration menu
- Exiting cal mode (b2=0) also triggers Err4
- **Aspirate only occurs on the normal→cal mode transition**; re-sending
  A5 b2=1 while already in cal mode does NOT aspirate again
- Source: FUN_140069c60 disassembly; `param` comes from `movsx edx, sil`
  at 0x140069ce1

**SetVolume / SendCaliVolume (0xA6):**

```
TX: [FE] [A6] [vol_hi] [vol_lo] [00] [cksum]
RX: [FD] [A6] [00]     [00]     [00] [A6]
```

- Volume encoded as `volume_µL × 10`, big-endian in bytes[2:3]
- Example: 200 µL → 2000 = 0x07D0 → `[FE A6 07 D0 00 7D]`
- **In normal mode**: sets the motor target volume for the NEXT cal mode
  entry (does not change display, does not move motor)
- **In cal mode**: changes the display volume (confirmed live — display
  updated from 100 to 50, 150, 200 etc.)
- Source: FUN_140069a10 disassembly; calling code at line 12254
  shows `iVar3 = param_2 * 10`

**WriteEE (0xA4):**

```
TX: [FE] [A4] [addr/val_hi] [addr/val_lo] [value] [cksum]
RX: [FD] [A4] [00]          [00]           [00]    [A4]
```

- Address and value encoding TBD — need write-then-read test to confirm
- Source: FUN_140069730 disassembly; takes params (addr, byte_index, value)
- Live confirmed: device ACKs with `fd a4 00 00 00 a4`

**Unknown command (0xA3):**

```
TX: [FE] [A3] [b2] [b3] [b4] [cksum]
RX: [FD] [A3] [??] [00] [00] [cksum]
```

- Response byte[2] varies (observed 0x00 and 0xFF in different states)
- The PetteCali receive handler (FUN_14001d850 line 14395) checks for
  0xA3 in byte[1] of RESPONSES and enters a calibration data parser
- May be used by the device to send calibration data asynchronously

**Aspirate (0xB3) — CONFIRMED live, motor movement (normal mode only):**

```
TX: [FE] [B3] [01] [00] [00] [B4]
RX: [FD] [B3] [00] [00] [00] [B3]   ← motor started
    [FD] [B3] [01] [00] [00] [B4]   ← motor finished (12 bytes total)
```

- `b2=0x01` triggers aspiration at the pipette's current display volume
- Returns a **double 6-byte response**: first packet (b2=0x00) = started,
  second packet (b2=0x01) = completed
- **Only works in normal mode** — rejected in calibration mode (returns
  single 6-byte response with b2=0x00, no motor movement)
- Volume is the display volume (or the last A6-set volume if cal mode
  was used to override it)

**Dispense (0xB0) — CONFIRMED live, motor movement (both modes):**

```
TX: [FE] [B0] [01] [00] [00] [B1]
RX: [FD] [B0] [00] [00] [00] [B0]
```

- `b2=0x01` triggers dispensing
- Returns a single 6-byte response (b2=0x00 = acknowledged)
- **Works in both normal and calibration modes** (confirmed live)
- `b2=0x00` does NOT trigger dispense (no response or different behavior)

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

### Fixed-volume mode (CONFIRMED, RELIABLE)

Set volume manually on the pipette, then control aspirate/dispense
remotely.  This is the proven reliable path.

```
┌─────────────────────────────────────────────────────────┐
│ Prerequisites:                                          │
│   - Set volume on pipette dial/buttons                  │
│   - Dismiss Err4 if showing (hold pipette button)       │
│                                                         │
│ 1. Handshake         [FE A5 00 00 00 A5]               │
│    → device ACKs     [FD A5 00 00 00 A5]               │
│                                                         │
│ 2. Aspirate (B3)     [FE B3 01 00 00 B4]               │
│    → motor started   [FD B3 00 00 00 B3]               │
│    → motor done      [FD B3 01 00 00 B4]  (12 bytes)   │
│                                                         │
│ 3. Dispense (B0)     [FE B0 01 00 00 B1]               │
│    → device ACKs     [FD B0 00 00 00 B0]               │
│                                                         │
│ Repeat 2-3 as needed.                                   │
└─────────────────────────────────────────────────────────┘
```

**Note:** If B3 aspirate is rejected (6-byte response instead of 12),
perform a cal-mode toggle first to clear stale state:
```
[FE A5 01 00 00 A6]  → enter cal (dismiss Err4)
[FE A5 00 00 00 A5]  → exit cal (dismiss Err4)
```
Then B3 will work.  This is needed after any previous cal mode use.

### Remote volume control (EXPERIMENTAL — NOT CONFIRMED)

A6 changes the display in calibration mode, but we could NOT confirm
it reliably changes the actual motor travel.  One test (EXP-019) appeared
to show A6=50 causing a 50 µL aspirate, but this could not be reproduced.

Calibration mode entry triggers a fixed homing cycle (aspirate + dispense)
that is NOT controlled by A6.  The homing cycle runs the same regardless
of the A6-set volume.

PetteCali likely uses A6 to set the display volume, and the user
physically presses the pipette button to aspirate at each calibration
measurement point.  The software does not trigger the aspirate.

**Status: remote volume control is NOT available through the known
protocol.  Volume must be set manually on the pipette.**

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
