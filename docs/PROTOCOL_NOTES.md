---
title: "Protocol notes"
status: "ACTIVE"
updated: "2026-04-06"
owner: "lambda biolab"
---

# Protocol notes

## Source strategy

Three lines of evidence, in order of precedence when they disagree:

1. **Live probing** against real hardware (CP2102 on macOS) — see
   [`EXPERIMENT_LOG.md`](EXPERIMENT_LOG.md).
2. **Serial captures** of the vendor calibration tool (PetteCali, native
   C++/Qt6 Windows app) talking to the device.
3. **Static analysis** of the vendor tool's binary to extract command
   byte values and packet-builder structure where live capture was
   ambiguous.

Everything in this file describes observed protocol behaviour. The
driver implementation is original code; no vendor binary or
decompilation output is committed.

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

```text
[HEADER] [CMD] [B2] [B3] [B4] [CHECKSUM]
 1 byte  1 byte 1    1    1     1 byte
```

**Header bytes:**

- Host → device: `0xFE`
- Device → host: `0xFD`

**Checksum:** simple byte sum of bytes[1] through bytes[4] (4 bytes),
truncated to 8 bits.  Confirmed live: packets with bad checksums get
no response.

The packet structure was extracted from the vendor calibration tool's
packet-builder functions (WriteEE, SendCaliVolume, HandShake/Start­Calibrate)
via static analysis and corroborated against live captures.

### Important: NOT 7 bytes

An early decompilation pass suggested 7-byte packets with separate
ADDR_HI/ADDR_LO/VAL_HI/VAL_LO fields. That was wrong — the decompiler's
high-level output obscured the Qt `QByteArray::append` call sequence.
Live captures and low-level analysis of the same packet-builder
functions confirmed 6-byte packets with three payload bytes (B2, B3, B4)
between CMD and CHECKSUM.

## Commands (CONFIRMED — disassembly + live)

| CMD byte | Name | Direction | Confirmed |
|---|---|---|---|
| `0xA0` | **HELLO** | host→dev | **live ✓ EXP-049** |
| `0xA1` | INFO | host→dev | live ✓ |
| `0xA2` | STA | host→dev | live ✓ |
| `0xA3` | EE_READ | host→dev | live ✓ |
| `0xA4` | EE_WRITE | host→dev | live ✓ |
| `0xA5` | DEMARCATE | host→dev | live ✓ (cal mode) |
| `0xA6` | DMRCT_VOLUM | host→dev | live ✓ (cal only) |
| `0xA7` | RESET | host→dev | live ✓ |
| `0xA8` | DMRCT_PULSE | host→dev | live ✓ |
| **`0xB0`** | **WOL (mode)** | host→dev | **live ✓ EXP-049** |
| **`0xB1`** | **SPEED** | host→dev | **live ✓ EXP-049** |
| **`0xB2`** | **PI_VOLUM** | host→dev | **live ✓ EXP-050 motor** |
| **`0xB3`** | **KEY (suck/blow)** | host→dev | **live ✓ EXP-050 motor** |
| `0xB4` | ST_VOLUM | host→dev | live ✓ |
| `0xB5` | ST_NUM | host→dev | live ✓ |
| `0xB6` | DI1_VOLUM | host→dev | live ✓ |
| `0xB7` | DI2_VOLUM | host→dev | live ✓ |

The byte values were observed in serial captures of the vendor
calibration tool and corroborated against the binary's packet-builder
functions during static analysis.

### Command details

**HandShake / StartCalibrate (0xA5):**

```text
TX: [FE] [A5] [param] [00] [00] [cksum]
RX: [FD] [A5] [00]    [00] [00] [A5]
```

- `param=0`: connection handshake / exit calibration mode (confirmed live)
- `param=1`: enter calibration mode — causes persistent Err4 on the
  pipette display.  Does NOT trigger motor movement by itself.
- Response is always `fd a5 00 00 00 a5` regardless of param value
- **WARNING:** A5 b2=1 causes persistent Err4 that survives reboots.
  Confirmed on two separate devices.  Only use when necessary.
- Source: serial capture of PetteCali's calibration workflow plus
  static analysis of its handshake/calibrate packet builder.

**SendCaliVolume (0xA6):**

```text
TX: [FE] [A6] [vol_hi] [vol_lo] [00] [cksum]
RX: [FD] [A6] [00]     [00]     [00] [A6]
```

- Volume encoded as `volume_µL × 10`, big-endian in bytes[2:3]
- Example: 200 µL → 2000 = 0x07D0 → `[FE A6 07 D0 00 7D]`
- **In cal mode**: changes the display volume (confirmed live — display
  updated from 100 to 50, 150, 200 etc.)
- **Does NOT control motor travel** — tested: A6=10 and A6=100 both
  aspirated the same amount.  Volume is set by physical dial only.
- Source: serial capture of PetteCali's calibration volume command,
  plus static analysis of the corresponding packet builder which
  multiplies the input by 10.

**WriteEE (0xA4) — CONFIRMED from PetteCali capture:**

```text
TX: [FE] [A4] [00] [ADDR] [VALUE] [cksum]
RX: [FD] [A4] [??] [00]   [00]   [cksum]
```

- **Address in byte[3], value in byte[4]** (confirmed from serial capture)
- Byte[2] is always 0x00 in observed writes
- PetteCali sends each write twice (retry pattern)
- Source: serial capture of PetteCali WriteData session (EXP-031)

**ReadEE (0xA3) — CONFIRMED from PetteCali capture:**

```text
TX: [FE] [A3] [00] [ADDR] [00] [cksum]
RX: [FD] [A3] [VALUE] [00] [00] [cksum]
```

- **Address in byte[3]** (NOT byte[2] — this is why earlier reads failed)
- Byte[2] of TX is always 0x00
- Response byte[2] contains the EEPROM value
- PetteCali reads addresses 0x80 through 0xAD sequentially, each twice
- Source: serial capture of PetteCali calibration session (EXP-031)

**Aspirate (0xB3) — CONFIRMED live, motor movement:**

```text
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

```text
TX: [FE] [B0] [01] [00] [00] [B1]
RX: [FD] [B0] [00] [00] [00] [B0]
```

- `b2=0x01` triggers dispensing AND serves as the "prime" command
  that enables B3 aspirate to work
- Returns a single 6-byte response (b2=0x00 = acknowledged)
- **Must be sent before B3** — B3 is rejected without a prior B0
- Works in both normal and calibration modes (confirmed live)
- `b2=0x00` does NOT trigger dispense

**INFO (0xA1) — 6-byte response with channel + range fields:**

```text
TX: [FE] [A1] [00] [00] [00] [A1]
RX: [FD] [A1] [type] [range_hi] [range_lo] [cksum]
```

- `type` (b2): `1` = single-channel, `2` = multi-channel
- `range_hi:range_lo` (b3, b4): max volume in µL, 16-bit big-endian
- Confirmed against the DLAB spec (`Communication_Protocol_CN.doc` §2)
- Decoding tracked in [#37](https://github.com/Lambda-Biolab/dpette-usb-driver/issues/37);
  our earlier "13-byte response, all zeros" observation was almost certainly
  two A1 replies arriving in one read buffer.

**STA (0xA2) — 11-byte long-format response (reserved):**

```text
TX: [FE] [A2] [00] [00] [00] [A2]
RX: [FD] [A2] [b2] [b3..b9 — 7 bytes] [cksum]
```

- Long-format response (header + cmd + 1 status byte + 7 data bytes + checksum = 11 bytes)
- Marked "暂无使用" (currently unused) in the DLAB spec §3 — payload semantics
  not documented by the vendor
- Confirmed against the DLAB spec (`Communication_Protocol_CN.doc` §3)

## Response format (CONFIRMED — live)

All observed device responses are 6 bytes:

```text
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

## Data receive handler — observed behaviour

The vendor tool's response handler (a Qt `QSerialPort::readyRead` slot)
shows the following shape, useful for understanding device timing:

1. `QIODevice::readAll()` collects available bytes.
2. A 6-byte frame assembler buffers incoming bytes until a full frame
   arrives.
3. Frames are validated by checking that byte[0] equals the RX header
   (`0xFD`).
4. Dispatch on byte[1]:
   - `0xA3` (EE_READ) enters a calibration data parser that maps each
     subsequent response to a specific EEPROM address via internal flags.
   - All other responses go through standard ACK handling.

A separate buffered parser exists for frames that arrive split across
multiple `readyRead` events, with the same dispatch and flag logic.

Per-read timeout: 1000 ms.

## Remote pipetting flow — initial findings (2026-04-06)

> **Superseded by EXP-050 below.** The flow in this section uses the
> physical dial for volume because remote volume control had not yet
> been discovered. Keep for the trace data; for the current correct
> protocol see "Remote volume control — CONFIRMED (EXP-050)".

### Pipetting sequence (hands-off, no Err4)

Tested on clean dPette 10-100 µL.  Set volume on the physical dial,
then control aspirate/dispense remotely.

```text
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

```text
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

```text
⚠️  [FE A5 01 00 00 A6]  — Enter Calibration Mode (A5 b2=1)
```

**What it does:** Puts the device into calibration mode and sets a
persistent flag that causes Err4 on every subsequent reboot.

**Confirmed damage:** Sent to two separate dPette devices (30-300 µL
and 10-100 µL).  Both now show Err4 on every power-on.  The error
must be dismissed with the physical button each time.

**Status:** No known fix.  The physical factory reset button does NOT
clear this flag.  PetteCali's ResetFactory does NOT clear it.  A full
3-step PetteCali calibration followed by WriteData also does NOT clear
it.  The error must be dismissed with the physical button on every
boot; all serial operations work normally after dismissal.

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

1. **Err4 prevention** — is there a clean way to enter/exit cal mode
   without triggering Err4?  PetteCali manages this somehow.
2. **Volume readback** — no command was found to read the current volume
   setting from the device.
3. **Persistent Err4** — no known way to clear the startup error; persists
   through PetteCali WriteData, ResetFactory, and the physical factory
   reset button.

## Next steps

1. **Proper recalibration** — use PetteCali with real weight measurements
   to write correct k/b values (the dummy calibration wrote k=1.2313,
   b=0.0000 which may affect accuracy).
2. **Err4 root cause** — deeper analysis of what flag is set and how to
   clear it without PetteCali.
