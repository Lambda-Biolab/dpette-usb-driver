#!/usr/bin/env python3
"""Test B0→B3 aspirate inside calibration mode with A6 volume.

Enter cal mode, set volume with A6, B0 prime, B3 aspirate.
Tests two different volumes to see if amount changes.

Dismiss Err4 before running. Tip on, water ready.
Logs to captures/live_log.txt

Run directly:
    python tools/quick_test.py
"""

import time

import serial

LOGFILE = "/Users/antoniolamb/repos/dpette-usb-driver/captures/live_log.txt"
_log = open(LOGFILE, "w")  # noqa: SIM115


def log(msg: str) -> None:
    print(msg)
    _log.write(msg + "\n")
    _log.flush()


def log_input(prompt: str) -> str:
    print(prompt, end="", flush=True)
    _log.write(prompt)
    _log.flush()
    result = input()
    _log.write(result + "\n")
    _log.flush()
    return result


ser = serial.Serial(
    port="/dev/cu.usbserial-0001",
    baudrate=9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=3.0,
)


def pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    ck = (cmd + b2 + b3 + b4) & 0xFF
    return bytes([0xFE, cmd, b2, b3, b4, ck])


def sr(p: bytes, wait: float = 0.5) -> bytes:
    ser.reset_input_buffer()
    ser.write(p)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


log("=== B0→B3 IN CALIBRATION MODE WITH A6 VOLUME ===")
log("Dismiss Err4 first. Tip on, water ready.")
log("")

# Step 1: Handshake
log_input("[1] Dismiss Err4, press ENTER: ")
r = sr(pkt(0xA5), wait=1.0)
log(f"  Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

# Step 2: Enter cal mode
log("")
log("[2] Entering cal mode...")
r = sr(pkt(0xA5, 0x01), wait=3.0)
log(f"  A5 b2=1: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log_input("  Dismiss Err4 if showing. Press ENTER when cal menu shows: ")

# Wait for any homing cycle to finish
log("  Waiting 5s for homing cycle...")
time.sleep(5.0)

# Step 3: Set volume to 30 µL with A6
log("")
log("[3] Setting A6=30 µL")
val = 30 * 10
hi = (val >> 8) & 0xFF
lo = val & 0xFF
r = sr(pkt(0xA6, hi, lo), wait=0.5)
log(f"  A6=30: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Does display show 30? ")
log(f"  >> {note}")

# Step 4: B0 prime in cal mode
log("")
log("[4] B0 prime in cal mode")
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"  B0: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Motor moved? ")
log(f"  >> {note}")

# Step 5: B3 aspirate in cal mode
log("")
log("[5] B3 aspirate in cal mode — tip in water, HANDS OFF")
log_input("  Press ENTER: ")
r = sr(pkt(0xB3, 0x01), wait=3.0)
ok = len(r) >= 12
log(f"  B3: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log(f"  Motor {'OK' if ok else 'REJECTED'}")
if ok:
    note = log_input("  How much water? (expecting ~30): ")
    log(f"  >> {note}")
    log_input("  Dispense over cup. Press ENTER: ")
    sr(pkt(0xB0, 0x01), wait=2.0)
    log("  Dispensed")

# Step 6: Now change to 300 µL
log("")
log("[6] Setting A6=300 µL (still in cal mode)")
val = 300 * 10
hi = (val >> 8) & 0xFF
lo = val & 0xFF
r = sr(pkt(0xA6, hi, lo), wait=0.5)
log(f"  A6=300: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Does display show 300? ")
log(f"  >> {note}")

# Step 7: B0 prime again
log("")
log("[7] B0 prime")
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"  B0: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

# Step 8: B3 aspirate at 300
log("")
log("[8] B3 aspirate — tip in water, HANDS OFF")
log_input("  Press ENTER: ")
r = sr(pkt(0xB3, 0x01), wait=3.0)
ok = len(r) >= 12
log(f"  B3: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log(f"  Motor {'OK' if ok else 'REJECTED'}")
if ok:
    note = log_input("  How much water? (expecting ~300): ")
    log(f"  >> {note}")
    log_input("  Dispense over cup. Press ENTER: ")
    sr(pkt(0xB0, 0x01), wait=2.0)
    log("  Dispensed")

# Step 9: Back to 30 to confirm
log("")
log("[9] Setting A6=30 µL again")
val = 30 * 10
hi = (val >> 8) & 0xFF
lo = val & 0xFF
r = sr(pkt(0xA6, hi, lo), wait=0.5)
log(f"  A6=30: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

log("")
log("[10] B0 prime")
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"  B0: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

log("")
log("[11] B3 aspirate — tip in water, HANDS OFF")
log_input("  Press ENTER: ")
r = sr(pkt(0xB3, 0x01), wait=3.0)
ok = len(r) >= 12
log(f"  B3: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log(f"  Motor {'OK' if ok else 'REJECTED'}")
if ok:
    note = log_input("  How much water? (expecting ~30): ")
    log(f"  >> {note}")
    log_input("  Dispense. Press ENTER: ")
    sr(pkt(0xB0, 0x01), wait=2.0)
    log("  Dispensed")

log("")
log("Was there a clear difference between 30 and 300?")
answer = log_input("Answer: ")
log(f">> {answer}")

ser.close()
log("\nDone.")
_log.close()
