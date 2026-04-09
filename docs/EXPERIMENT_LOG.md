---
title: "Experiment log"
status: "ACTIVE"
updated: "2026-04-06"
owner: "lambda biolab"
---

# Experiment log

Chronological record of all live hardware tests, results, and dead ends.
Each entry includes the script used, what was tested, and the outcome.

## Session: 2026-04-06

Hardware: dPette 30-300 µL, CP2102 on `/dev/cu.usbserial-0001`, macOS

---

### EXP-001: Passive listen (pre-handshake)

**Script:** `tools/passive_listen.py`
**Hypothesis:** Pipette sends data when buttons are pressed
**Result:** ❌ Zero bytes received in 30 seconds
**Conclusion:** Device only responds to host commands; no unsolicited data

---

### EXP-002: Brute-force header byte

**Script:** `tools/brute_header.py`
**Hypothesis:** One of 256 possible header bytes triggers a response
**Result:** ❌ Zero responses (sent 7-byte packets — wrong size)
**Conclusion:** Dead end due to incorrect packet size assumption (7 bytes).
Later corrected to 6 bytes.

---

### EXP-003: Confirm header and command bytes from disassembly

**Script:** `tools/probe_handshake.py` (v1, 7-byte packets)
**Hypothesis:** Header=0xAA, CMD bytes from agent analysis
**Result:** ❌ No responses with 7-byte packets
**Dead end:** The agent's byte constant extraction was from the installer,
not the app binary. The 7-byte format was wrong.

---

### EXP-004: Correct to 6-byte packets with 0xFE header

**Script:** `tools/probe_handshake.py` (v2, 6-byte packets)
**Source:** Instruction-level disassembly of `PetteCali.exe` confirmed
`mov edx, 0xfffffffe` (header), `mov edx, 0xffffffa4` (WriteEE),
`mov edx, 0xffffffa6` (SendCaliVolume), `mov edx, 0xffffffa5` (HandShake)
**Result:** ✅ **FIRST CONTACT** — HandShake responded:
```
TX: fe a5 00 00 00 a5
RX: fd a5 00 00 00 a5
```
**Key finding:** TX header=0xFE, RX header=0xFD, 6-byte packets, checksum validated

---

### EXP-005: EEPROM read attempts

**Scripts:** `tools/read_eeprom.py`, `tools/read_eeprom2.py`, `tools/read_eeprom3.py`
**Hypothesis:** CMD=0xA6 with address reads EEPROM data
**Result:** ❌ All addresses return identical responses (0x00 or 0x01 in byte[2])
depending on address range, not actual EEPROM data
**Dead end:** 0xA6 is NOT a read command — it's SendCaliVolume. The "address"
we were sending was interpreted as a volume value.

---

### EXP-006: Address sweep

**Script:** `tools/sweep_addresses.py`
**Result:** Binary threshold: addresses 0x00-0x36 → response b2=0x00,
addresses 0x37-0xFF → response b2=0x01. Not actual data.
**Conclusion:** Confirmed A6 is not a per-address read command.

---

### EXP-007: Probe all command variants

**Script:** `tools/probe_response_format.py`
**Key findings:**
- Bad checksums → no response (checksum IS validated)
- 7-byte packets → no response (format IS 6 bytes)
- CMD=0xA3 returns different byte[2] values depending on device state

---

### EXP-008: EEPROM write-read test

**Script:** `tools/eeprom_write_read.py`
**Hypothesis:** Write 0x42 to addr 0x88, read back to confirm protocol
**Result:** ❌ All reads returned identical data before and after writes.
Three write format hypotheses all failed to produce readable changes.
**Dead end:** Either writes didn't take effect, or we don't know how to read.

---

### EXP-009: Passive listen post-handshake

**Script:** `tools/listen_after_handshake.py`
**Hypothesis:** After handshake, button presses send data
**Result:** ❌ Zero bytes in 60 seconds. Physical buttons are handled locally.
**Conclusion:** Motor control is internal; serial is calibration-only by design.

---

### EXP-010: CMD brute-force (0x00-0xFF)

**Script:** `tools/brute_cmd.py`
**Result:** ✅ **MAJOR DISCOVERY** — 17 responding commands:
- 0xA0-0xA8 (calibration range, previously known)
- **0xB0-0xB7** (new range! previously untested)
- 0xA1, 0xA2 return **13-byte** responses (not 6)

---

### EXP-011: Interactive motor command identification

**Script:** `tools/interactive_probe.py` (run by user in terminal)
**Result:** ✅ **MOTOR CONTROL FOUND:**
- **B3 b2=0x01 = ASPIRATE** — 12-byte double response, confirmed motor movement
- **B0 b2=0x01 = DISPENSE** — 6-byte response, confirmed motor movement
- B1, B2, B4-B7 = no visible effect
**Key finding:** Volume = whatever the pipette display shows

---

### EXP-012: State read before/after aspirate

**Script:** `tools/auto_aspirate_state.py`
**Hypothesis:** A1/A2 13-byte responses change after motor movement
**Result:** ❌ All responses identical across 5 state reads (before/after
aspirate and dispense). No motor position or volume data exposed.
**Dead end:** Device doesn't expose internal state over serial.

---

### EXP-013: Volume control via B-range payloads

**Script:** `tools/interactive_volume.py`
**Hypothesis:** B1-B7 with volume-encoded payloads change the display
**Result:** ❌ No display changes from any B-range command with volume data.
Tested with ×10 encoding, raw encoding, and b4=1 trigger flag.
**Dead end:** B-range commands don't control volume.

---

### EXP-014: Volume increment/decrement via B-range

**Script:** `tools/interactive_vol_increment.py`
**Hypothesis:** B1-B7 sent repeatedly act as volume up/down
**Result:** ❌ No display changes after 3× sends per command.
**Dead end:** B-range is not volume increment/decrement.

---

### EXP-015: Volume change detection

**Script:** `tools/read_volume_change.py`
**Hypothesis:** A1/A2 or B-status changes when user adjusts volume dial
**Result:** ❌ All responses identical before and after manual volume change.
**Conclusion:** Current volume is not readable over serial.

---

### EXP-016: A6 as volume setter (first attempt)

**Script:** `tools/test_a6_then_aspirate.py`
**Hypothesis:** A6 sets motor travel, then B3 aspirates at that volume
**Results (display at 100 µL):**
- A6=30 → drew 30 µL ← appeared to work!
- A6=150 → drew 100 µL ← did not work
- A6=300 → drew 100 µL ← did not work
**Status:** Inconclusive — 30 µL result later contradicted (see EXP-017)

---

### EXP-017: A6 volume test at max display (300 µL)

**Script:** `tools/test_a6_at_max.py`
**Result:** ❌ ALL volumes drew 300 µL regardless of A6 value.
A6 has no effect on B3 aspirate in normal mode.
**Conclusion:** EXP-016's 30 µL result was likely measurement error.
A6 does NOT control motor travel in normal mode.

---

### EXP-018: Calibration mode exploration

**Script:** `tools/test_cali_mode.py`
**Result:** ✅ **BREAKTHROUGH:**
- A5 b2=1 enters calibration mode (different display menu)
- **A6=50 changed display to 50 µL in cal mode**
- **A6=150 changed display to 150 µL in cal mode**
- B3 aspirate rejected in cal mode
- A5 b2=0 exits cal mode (triggers Err4)
**Key finding:** A6 IS remote volume control — but only in calibration mode.

---

### EXP-019: Volume persistence after cal mode

**Script:** `tools/test_cali_volume_persist.py`
**Result:** Partial success:
- Set 50 µL via cal mode → aspirate drew 50 µL ✅
- Set 150 µL via cal mode → aspirate drew 50 µL ❌ (first value stuck)
- Set 250 µL via cal mode → aspirate drew 50 µL ❌
**Conclusion:** A6 volume may only take effect once per session.

---

### EXP-020: Fresh reboot + single A6=200

**Script:** `tools/test_a6_single_200.py`
**Result:** ❌ Aspirate did nothing (6-byte rejected response).
Serial aspirate broken after repeated cal mode experiments.
**Side effect:** Err4 now persists across reboots.

---

### EXP-021: Error recovery attempts

**Script:** `tools/fix_err4.py`
**Attempted:** EEPROM zeroing, A0/A3/A7 reset variants, cal mode cycle
**Result:** ❌ Err4 still persists. Serial aspirate still rejected.
**Side effect:** EEPROM writes to 0x80-0xAF may have been destructive.

---

### EXP-022: PetteCali WriteData (via Parallels VM)

**Tool:** PetteCali v2.1.0.0 on Windows 11 (Parallels)
**Result:** ✅ Connected, completed 3-step dummy calibration, "WriteEE
Sucessed". Wrote k=1.2313, b=0.0000.
**Side effect:** Err4 STILL persists on reboot. But this properly
completed the calibration session in the device's state machine.

---

### EXP-023: Cal mode toggle restores serial aspirate

**Script:** `tools/exit_cal_and_test.py`
**Result:** ✅ **FIX FOUND:**
```
Handshake (A5 b2=0) → Enter cal (A5 b2=1) → Exit cal (A5 b2=0) → B3 aspirate WORKS
```
The cal mode toggle clears the stale state that blocks B3.
Motor OK — 12-byte double response confirmed.

---

### EXP-024: Cal mode aspirate trigger

**Script:** `tools/test_cal_aspirate.py`
**Hypothesis:** Find what triggers aspirate inside calibration mode
**Tested in cal mode:** A5 b2=1, B3 (b2=0/1/2), A3 (b2=0/1), A6 re-send,
A0 (b2=0/1), A7 (b2=0/1), B1-B7 (b2=1)
**Result:** ❌ None triggered motor movement while already in cal mode.

---

### EXP-025: A6 before cal entry triggers aspirate

**Script:** `tools/test_cal_aspirate.py` (v2)
**Result:** ✅ **VOLUME CONTROL CONFIRMED:**

| A6 volume | Display | Motor aspirated on cal entry? |
|-----------|---------|-------------------------------|
| 100 µL    | 100 µL  | No (same as display)          |
| 200 µL    | 100 µL  | **Yes**                       |
| 300 µL    | 100 µL  | **Yes**                       |
| 150 µL    | (in cal)| No (re-sent A5 b2=1 in cal)   |

**Conclusion:** The complete remote pipetting flow is:
1. `A5 b2=0` (handshake)
2. `A6` (set volume)
3. `A5 b2=1` (enter cal mode = ASPIRATE at A6 volume)
4. `B0 b2=1` (dispense)
5. `A5 b2=0` (exit cal mode)
6. Repeat from step 2

---

## Dead end summary

| Area | What we tried | Why it failed |
|------|--------------|---------------|
| EEPROM read | A6 with addresses, A4 with addresses, A1/A2 bulk | A6 is volume not read; read protocol unknown |
| EEPROM write-read | A4 write + read back | Can't confirm writes; read protocol unknown |
| Volume via B-range | B1-B7 with payloads, increments | B-range doesn't control volume |
| Volume readback | All cmds before/after dial change | Volume not exposed over serial |
| A6 in normal mode | A6 before B3 aspirate | A6 only affects cal mode entry aspirate |
| Aspirate in cal mode | B3, A3, A0, A7, B1-B7, A5 re-entry | Only initial A5 b2=1 transition aspirates |
| Err4 clearing | Factory reset, EEPROM zero, A0/A3/A7, PetteCali WriteData+ResetFactory | Err4 persists; can only dismiss with button |

### EXP-026: Visual volume verification with water

**Script:** `tools/quick_test.py` (corrected flow version)
**Hypothesis:** Enter cal mode → A6 sets volume → exit → re-enter triggers
aspirate at that volume
**Result:** ❌ Inconclusive. Cal mode entry always triggers a standard
homing cycle (full aspirate + dispense) that must complete before any
commands are accepted. Err4 blocks commands during homing. Re-entering
cal mode triggers another Err4 + homing, making it impossible to isolate
the A6-set volume aspirate from the homing cycle.
**Conclusion:** The cal mode homing cycle is a fixed sequence, not
controlled by A6. Remote volume control via this path is NOT confirmed.

### Updated dead end: Remote volume control

The A6 command changes the display in cal mode, but we could NOT confirm
it changes the actual motor travel. The single 50 µL result in EXP-019
could not be reproduced. The most likely explanation: PetteCali sets the
display volume with A6, and the USER physically presses the pipette button
to aspirate at each calibration measurement point. The software does not
trigger the aspirate — the operator does.

**Remote volume control status: UNCONFIRMED / LIKELY NOT POSSIBLE
through the calibration protocol alone.**

### EXP-027: Clean device test (10-100 µL dPette)

**Device:** Second dPette, 10-100 µL range, never touched before
**Results:**
- Handshake works ✓
- B3 b2=1 alone → REJECTED (same as corrupted device)
- A5 b2=1 (enter cal) → causes persistent Err4, NO motor movement
- B0 b2=1 in cal mode → motor moved (small aspirate)
- A6 does NOT control motor travel (A6=10 and A6=100 same amount)
**Conclusion:** B3 rejection is normal behavior, not corruption.
A5 b2=1 causes Err4 on clean devices too.

---

### EXP-028: B0 primes B3 — definitive hands-off test

**Device:** 10-100 µL dPette (in cal mode state from EXP-027)
**Sequence:** Handshake → B0 b2=1 → B3 b2=1
**Result:** ✅ **B3 WORKS after B0 prime!**
- B0 b2=1: 6-byte ACK
- B3 b2=1: 12-byte double response, motor aspirated
- Repeated 3 times successfully
- **No Err4, no button press, hands completely off pipette**
**Conclusion:** B0 b2=1 is a required "prime" command that enables B3.
Without B0, B3 is always rejected.

---

### EXP-029: Volume follows physical dial

**Device:** 10-100 µL dPette
**Test:** Dial at 100 µL → handshake → B0 → B3 → aspirated ~100 µL
**A6 test:** A6=10 sent before B0/B3 → aspirated same amount (not 10)
**Conclusion:** Volume = physical dial setting. A6 does NOT control
motor travel.

---

### CORRECTION: Earlier motor observations were physical button presses

EXP-011 (B3 "aspirate" discovery), EXP-019 (50 µL volume control),
and EXP-025 (cal mode aspirate) all involved dismissing Err4 with
the physical button during testing. The motor movements attributed
to serial commands were actually caused by the button presses.

The definitive test (EXP-028) with hands completely off the pipette
confirmed the true working sequence: B0 prime → B3 aspirate.

---

### EXP-030: Extreme volume test (30 vs 300 µL) — definitive

**Device:** 30-300 µL dPette (with dummy calibration from prior experiments)
**Sequence:** Handshake → B0 prime (once) → B3 at 300 → B0 dispense →
B3 at 30 → B0 dispense → B3 at 300 → B0 dispense
**Results:**

| Dial | B3 aspirated | Notes |
|------|-------------|-------|
| 300  | ~12 µL      | First after B0 prime — priming artifact |
| 30   | **~30 µL**  | Correct |
| 300  | **~300 µL** | Correct |

**B0 behavior:** dispenses full amount + small re-aspirate at end (priming
the piston for the next B3 cycle).

**Conclusion:** ✅ **VOLUME FOLLOWS THE PHYSICAL DIAL — CONFIRMED.**
The first B3 after a B0 prime draws a small amount (priming artifact).
Subsequent B3 commands aspirate at the dial volume.  The 10x difference
between 30 and 300 µL was unmistakable.

---

### EXP-031: PetteCali serial capture (via Parallels VM)

**Tool:** Free Device Monitoring Studio on Windows 11 (Parallels),
sniffing COM3 while PetteCali ran a full calibration + WriteData.
**Captures:** `~/Documents/DMS Log Files/*.dmslog8`

**CRITICAL FINDINGS — EEPROM read/write format:**

Read: `FE A3 00 [ADDR] 00 [CHECKSUM]` — address in byte[3]!
Write: `FE A4 00 [ADDR] [VALUE] [CHECKSUM]` — address in byte[3], value in byte[4]!

All our prior EEPROM attempts failed because we put the address in byte[2].

**PetteCali calibration sequence observed:**
1. `FE A8 01 68 09 38` — device config/init
2. `FE A0 00 00 00 A0` — status check (×2)
3. `FE A3 00 80..AD` — read all EEPROM (46 addresses, each sent twice)
4. `FE A5` — handshake
5. `FE A6 03 E8` — set cal volume 100 µL (1000 ÷ 10)
6. `FE A6 07 D0` — set cal volume 200 µL (2000 ÷ 10)
7. `FE A6 0B B8` — set cal volume 300 µL (3000 ÷ 10)
8. `FE A5` — handshake close

**WriteData sequence:**
- `FE A4 00 90..9F [VALUE]` — write k/b coefficients (seg1 + seg2)
- `FE A0` — status check
- `FE A3 00 80..AD` — re-read all EEPROM to verify
- Each write sent twice (retry pattern)

**WriteEE values captured (k=1.2268, b=0.0000):**
- 0x90: 0x00, 0x91: 0x00, 0x92: 0x2F, 0x93: 0xEC (k bytes)
- 0x94-0x97: all 0x00 (b bytes)
- 0x98-0x9F: same pattern for seg2

---

### Summary of confirmed working protocol

```
Handshake  [FE A5 00 00 00 A5]
B0 prime   [FE B0 01 00 00 B1]  ← once per session, primes piston
B3 aspirate [FE B3 01 00 00 B4] → 12-byte response, aspirates at dial vol
B0 dispense [FE B0 01 00 00 B1] → dispenses + re-primes for next B3
Repeat B3 → B0 as needed
```

Volume = physical dial setting.  No remote volume control.
Tested on both 10-100 µL (clean) and 30-300 µL (recalibrated) devices.

### EXP-032: Full EEPROM scan (0x00-0xFF) and Err4 flag hunt

**Device:** 30-300 µL dPette
**Result:** Full EEPROM dump revealed:
- 0x00: zero (only zero among surrounding 0xFF bytes)
- 0x01-0x3F: all 0xFF (unused/erased EEPROM)
- 0x42: 0x00 (zero among 0xFF — tested as Err4 flag, NOT it)
- 0x60-0x67: `56 65 72 34 2E 32 2E 33` = ASCII **"Ver4.2.3"** (firmware version!)
- 0x80-0xAF: calibration data (k/b coefficients — confirmed by PetteCali)
- 0xB2-0xB3: 0x01 0x2C = 300 (max volume for 30-300 model)
- 0xD2-0xD3: 0x0B 0xB8 = 3000 (300 µL × 10)

**Err4 flag tests:**
- Wrote 0xFF to 0x42 → error changed to Err2, restored to 0x00
- Wrote 0x00 to 0xC4/0xC5 → no change
- Wrote 0x03 to 0x80 (cal point count) → no change
- Replicated full PetteCali sequence (A8→A0→A3 reads→A5→A6→A5) → no change

**Conclusion:** Err4 is NOT stored in EEPROM. It is in MCU internal
flash/registers not accessible via the serial protocol. Err4 is cosmetic —
pipette and serial commands work normally after dismissing with button.

---

### EXP-033: A8 init command test

**Command:** `FE A8 01 68 09 38` (exact bytes from PetteCali capture)
**Result:** No response. A8 with other parameters echoed as A6.
A8 may require specific device state (pre-handshake?) to work.

---

### EXP-039: Physical button aspirate at A6-set volume in cal mode

**Device:** 30-300 µL dPette
**Flow:** Enter cal mode → A6 sets display volume → user presses physical
button → observe aspirated amount
**Results:**

| Round | A6 volume | Physical button | Water drawn |
|-------|-----------|----------------|-------------|
| 1     | 30 µL     | pressed        | **~30 µL**  |
| 2     | 300 µL    | pressed        | **~300 µL** |
| 3     | 30 µL     | pressed        | **~30 µL**  |

✅ **VOLUME CONTROL CONFIRMED!**

A6 sets the target volume. The physical button triggers aspiration at
that volume. Volume can be changed between aspirations by sending A6
again — no need to exit/re-enter cal mode.

This is exactly how PetteCali's calibration works: software sets the
volume, user presses the button to aspirate at each measurement point.

**Complete remote volume control flow (requires physical button actuation):**
1. Enter cal mode: `FE A5 01 00 00 A6` (dismiss Err4)
2. Set volume: `FE A6 [vol_hi] [vol_lo] 00 [cksum]` (vol = µL × 10)
3. Physical button press → aspirates at A6 volume
4. Change volume: send new A6 → button press → aspirates at new volume
5. Repeat 2-4 for each volume

**Remaining blocker:** The physical button press cannot be triggered via
serial. For full automation, need either:
- Physical actuator (servo/solenoid) on the button
- RP2040 MitM intercepting the button GPIO line
- Firmware patch to add a serial button-press command

---

### EXP-042: Full 0x00-0xFF CMD scan in calibration mode

**Device:** 30-300 µL dPette, in cal mode, A6=100 µL
**Result:** Same 16 commands respond as in normal mode. No cal-mode-only
commands exist. No motor movement during scan except B0 priming.

---

### EXP-043: B0 payload, b2 variants, rapid-fire, A6 encoding in cal mode

**B0 payload in cal mode:** b3/b4 ignored — all drew ~30 µL regardless
of volume encoding (30/100/300 µL×10).

**B0 b2 variants:** b2=1,2,3 all move motor (same fixed amount).
b2=4,5,FF do nothing. b2=2 and b2=3 are equivalent to b2=1.

**Rapid-fire B0:** Five B0 commands did NOT accumulate steps. Same
amount as single B0.

**Raw A6 encoding:** A6 with 0x012C (300 raw) displayed "30" — confirms
A6 always divides by 10. B0 amount unchanged.

---

### EXP-044: B0 b2=1/2/3 at different A6 volumes in cal mode

**Tested:** B0 b2=1, b2=2, b2=3 each at A6=30 and A6=300 µL.
**Result:** ❌ All six combinations drew the same fixed amount (~30 µL).
None of the b2 variants are volume-controlled. B0 in cal mode is always
a fixed priming cycle regardless of A6 volume or b2 value.

---

### EXP-045: A6 persistence after cal mode exit

**Hypothesis:** A6-set volume might persist in MCU RAM after exiting
cal mode. B3 in normal mode might use the A6 value instead of dial.
**Setup:** Dial at 150 µL. Enter cal → A6 → exit cal → B3 (no B0).
**Result:**

| A6 value | B3 drew | Matches |
|----------|---------|---------|
| 300 µL   | 150 µL  | Dial ✗  |
| 30 µL    | 150 µL  | Dial ✗  |
| 300 µL   | 150 µL  | Dial ✗  |

❌ A6 does NOT persist. MCU reverts to dial volume on cal exit.
B3 always uses dial volume in normal mode. The EXP-019 result (50 µL
matching A6) was coincidence or measurement error.

**Also confirmed:** B3 works without B0 prime after cal mode exit
(12-byte response, motor OK). The cal exit itself acts as a prime.

---

### EXP-046: Expert follow-up — DTR/RTS, UART break, fast timing

**Q1 DTR/RTS in cal mode:** DTR pulse, RTS pulse, DTR+RTS together —
no motor movement. Not wired to button GPIO.

**Q2 UART break/special bytes in cal mode:** Break condition, null flood
(50 bytes), raw 0xB3 without header, rapid A5 b2=1 ×10 — no motor.

**Q4 Fast timing:** A6→B0 within 20ms, A6→B3 within 20ms,
A5→A6→B0 all within 20ms — B0 moved motor (same fixed priming as
always), B3 still rejected. Timing does NOT change behavior.

**A6→B0 timing comparison:** Slow (2s gap) vs fast (20ms gap) at
A6=300 and A6=30 — all drew same ~40-50 µL. Timing irrelevant.

---

### EXP-047: CMD scan b2=0x00 and b2=0x02/03/FF in cal mode

**Scan 1:** All 256 CMDs with b2=0x00 in cal mode. Same 16 commands
respond as with b2=0x01. No motor movement. No new commands.

**Scan 2:** Responding CMDs with b2=0x02, 0x03, 0xFF. Motor moved
during scan (likely B0 b2=0x02 or b2=0x03 — same fixed priming
confirmed in EXP-043). Notable: B5 b2=0x03 returned byte[2]=0x00
(different from usual 0x01), A6 b2=0xFF returned byte[2]=0x01.

**Conclusion:** No new commands or behaviors found. The entire b2
parameter space (0x00, 0x01, 0x02, 0x03, 0xFF) has been tested
for all responding commands in cal mode.

---

### EXP-048: Full automation cycle — A6→button→B0→repeat

**The definitive automation test.** In cal mode, tested the complete
cycle with volume changes between aspirations.

| Step | Method | Volume | Result |
|------|--------|--------|--------|
| A6=300 | serial | — | display changed ✓ |
| Aspirate | physical button | 300 µL | ✅ correct |
| Dispense | B0 serial | — | ✅ dispensed |
| A6=100 | serial | — | display changed ✓ |
| Aspirate | physical button | 100 µL | ✅ correct |
| Dispense | B0 serial | — | ✅ dispensed |

**Also confirmed:**
- B0 dispense works immediately after button aspirate in cal mode ✓
- A6 can change volume between cycles without exiting cal mode ✓
- B3 is rejected in cal mode (as expected) ✓
- No need to exit/re-enter cal mode between cycles ✓

**Confirmed automation flow (requires MOSFET on button):**
```
Enter cal mode (once) → for each cycle:
  A6 set volume (serial) → button press (MOSFET) → B0 dispense (serial)
```

This is the architecture for a $140 fully programmable pipette:
$130 dPette + BSS138 MOSFET ($0.10) + RP2040 ($4) + 2 solder joints.

---

### ~~FINAL CONCLUSION: Serial-only volume control is NOT possible~~

**OVERTURNED by EXP-050 (2026-04-09).** Serial volume control IS possible
using the remote control protocol (A0/B0/B2/B3) instead of the calibration
interface (A5/A6). See EXP-049 and EXP-050 for details.

The original conclusion was correct within its scope — the calibration
interface (A5/A6) does NOT provide volume control. But the remote control
interface (B2 PI_VOLUM + B3 KEY) was never tested in the correct sequence
because it was not discovered through PetteCali decompilation.

---

### EXP-040: Interactive prime+B3 isolation in cal mode

**Device:** 30-300 µL dPette, in cal mode, A6=100 µL
**Method:** Sent each of 26 prime commands (B0-B7 b2=0/1, A0/A3/A4/A6/A7
b2=0/1) one at a time with user observation, followed by B3 b2=1.
**Result:** ❌ Only B0 b2=1 (test 1/26) caused motor movement — the same
small fixed priming, not volume-controlled. B3 was rejected after every
prime (6-byte response, no motor).
**Conclusion:** Definitive — no serial command enables B3 aspirate in
calibration mode. The physical button is the ONLY way to trigger
aspiration at the A6-set volume.

### EXP-041: A7 deep dive in cal mode

**Device:** 30-300 µL dPette, in cal mode
**Tested:** A7 with b2=0/1/2/3/FF, and with volume payloads (100×10,
300×10) in b3/b4
**Result:** ❌ No motor movement from any A7 variant. All returned
`fd a7 00 00 00 a7`. Earlier motor movement attributed to A7 was
residual from B0 priming in the fast scan.

---

### EXP-036: Complement pair write to 0x42/0x43

**Hypothesis:** Err4 flag is a byte+complement pair at 0x42 (0x00) / 0x43 (0xFF).
Writing 0xFF/0x00 as a valid complement would signal "calibration complete."
**Result:** ❌ Wrote 0x42=0xFF, 0x43=0x00 (valid XOR complement). Values
persisted after reboot — MCU did not overwrite. Err4 still appeared.
**Conclusion:** 0x42/0x43 are NOT the Err4 flag. The flag is not in EEPROM.

---

### EXP-037: Extended A3 address reads (beyond 0xFF)

**Hypothesis:** If MCU is STM8-like, byte[2] in A3 command might be addr_hi,
allowing reads of program flash (0x8000+) or option bytes (0x4800+).
**Result:** ❌ Byte[2] is ignored. 0x4042 returns same as 0x42, 0x8001
returns same as 0x01. Cannot access memory beyond 0x00-0xFF.
**Conclusion:** A3 reads are limited to 256-byte EEPROM. No flash access.

---

### EXP-038: B0→B3 aspirate inside calibration mode

**Hypothesis:** B0 primes B3 in normal mode. Does B0→B3 also work in cal mode
where A6 controls the display volume?
**Tested:** Enter cal → A6=30 → B0 → B3 → A6=300 → B0 → B3 → A6=30 → B0 → B3
**Result:** ❌ B3 rejected in all three attempts (6-byte response, no motor).
B0 moved the motor but only as a small fixed priming cycle — not volume-controlled.
A6 changed the display to 30 and 300 correctly.
**Conclusion:** B3 does not work in cal mode, even with B0 prime. B0's movement
in cal mode is a fixed prime, not an aspirate at A6 volume. Cal mode does not
provide volume-controlled aspiration via serial.

---

### EXP-034: DTR/RTS line manipulation

**Device:** 30-300 µL dPette
**Hypothesis:** CP2102 DTR/RTS lines may be wired to MCU reset/boot pins
**Tested:**
- DTR toggle (reset) — no display change
- RTS toggle — no change
- DTR+RTS together (boot mode) — no change, no bootloader response
- DTR low + RTS high (BOOT0 entry) — no bootloader response
- Rapid DTR pulses — no change
- UART break condition — no change
- STC sync byte (0x7F) at 9600/115200/19200/4800/1200 — no response
- STM32 sync byte — no response
**Conclusion:** DTR/RTS are NOT wired to MCU reset/boot pins.
No bootloader detected on any baud rate.

---

### EXP-035: stcgal STC bootloader detection

**Tool:** stcgal v1.10 (Python)
**Method:** stcgal listens on serial port while pipette is power-cycled
(powered off and on while USB stays connected)
**Tested at:** 9600, 115200, 2400 baud
**Result:** No STC bootloader detected at any baud rate.
**Conclusion:** MCU is likely NOT an STC family chip.
Identifying the MCU requires opening the device and reading chip markings.

---

### EXP-049: Official DLAB remote control protocol test (2026-04-09)

**Source:** Communication_Protocol_CN.doc from xg590/Learn_dPettePlus repo —
the official DLAB serial protocol document shipped with the dPette+.

**Key discovery:** The official protocol defines a completely different
workflow from what we've been using (A5/A6 calibration interface from
PetteCali). The remote control interface uses A0/B0/B1/B2/B3.

**Device:** dPette on /dev/cu.usbserial-0001
**Script:** `examples/test_remote_mode.py`
**Results:**
- A0 handshake: accepted (p1=0) — this is the REAL handshake, not A5
- B0 param=1 (enter PI mode): accepted, motor homed
- B1 speed control (suck=2, blow=2): both accepted
- B2 PI_VOLUM = 200 uL (24-bit × 100 encoding): accepted (p1=0)
- B3 param=1 (aspirate): 12-byte response, motor moved
- B3 param=2 (dispense): 12-byte response, motor moved — FIRST TIME TESTED

**Conclusion:** The entire official remote protocol works on the basic
dPette. B3 b2=2 for dispense is confirmed working (never tested in 48
prior experiments). B2 volume was accepted but needed volume verification.

---

### EXP-050: B2 volume control verification (2026-04-09)

**Device:** dPette 30-300 uL, physical dial set to 300 uL
**Script:** `examples/test_b2_volume.py`
**Method:** Three trials — B2=50, B2=200, B2=50 — with dial fixed at 300.
If motor travel matches B2 (not dial), volume control is confirmed.

**Results:**
- Trial 1 (B2=50 uL): motor moved, display changed to 50, SMALL aspirate
- Trial 2 (B2=200 uL): motor moved, display changed to 200, MEDIUM aspirate
- Trial 3 (B2=50 uL): motor moved, display changed to 50, SMALL aspirate

**All three volumes matched B2 setting, NOT the 300 uL dial.**
Display updated to show B2 volume. Liquid volumes visibly different
between 50 and 200 uL trials.

**CONCLUSION: Remote serial volume control is CONFIRMED.**

The correct workflow is:
```
A0 (handshake) → B0 param=1 (PI mode) → B2 vol×100 (set volume) → B3 param=1 (aspirate) → B3 param=2 (dispense)
```

This overturns the EXP-044 "FINAL CONCLUSION" that serial-only volume
control is not possible. The previous 44 experiments tested the calibration
interface (A5/A6 from PetteCali), not the remote control interface (A0/B0/B2/B3
from the official DLAB protocol). No MOSFET or hardware modification is needed.

---

## Known side effects from experiments

1. **Persistent Err4 on 30-300 device** — from EXP-018 cal mode entry.
   Dismiss with button. PetteCali WriteData clears it.
2. **Persistent Err4 on 10-100 device** — from EXP-027 cal mode entry.
   Same behavior.
3. **Dummy calibration on 30-300 device** — k=1.2313, b=0.0000 written
   by PetteCali (EXP-022). Needs proper recalibration.
