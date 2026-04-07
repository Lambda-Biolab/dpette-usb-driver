#!/usr/bin/env python3
"""Test physical button aspirate at A6-set volume in cal mode.

Enter cal mode, set volume with A6, then YOU press the physical button.
Compare water levels at 30 vs 300 µL.

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


log("=== PHYSICAL BUTTON ASPIRATE AT A6 VOLUME ===")
log("In cal mode, A6 sets the display volume.")
log("YOU press the pipette button to aspirate.")
log("This is exactly what PetteCali expects the user to do.")
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
log_input("  Dismiss Err4, wait for homing to finish. Press ENTER: ")
time.sleep(3.0)

# Round 1: A6=30
log("")
log("=" * 50)
log("ROUND 1: A6 = 30 µL")
log("=" * 50)
val = 30 * 10
hi = (val >> 8) & 0xFF
lo = val & 0xFF
r = sr(pkt(0xA6, hi, lo), wait=0.5)
log(f"  A6=30: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Display shows 30? ")
log(f"  >> {note}")
log("")
log("  Dip tip in water.")
log("  NOW PRESS THE PHYSICAL ASPIRATE BUTTON on the pipette.")
note = log_input("  How much water did it draw? ")
log(f"  >> {note}")
log_input("  Dispense manually (press button again). Press ENTER when done: ")

# Round 2: A6=300
log("")
log("=" * 50)
log("ROUND 2: A6 = 300 µL")
log("=" * 50)
val = 300 * 10
hi = (val >> 8) & 0xFF
lo = val & 0xFF
r = sr(pkt(0xA6, hi, lo), wait=0.5)
log(f"  A6=300: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Display shows 300? ")
log(f"  >> {note}")
log("")
log("  Dip tip in water.")
log("  NOW PRESS THE PHYSICAL ASPIRATE BUTTON on the pipette.")
note = log_input("  How much water did it draw? ")
log(f"  >> {note}")
log_input("  Dispense manually. Press ENTER when done: ")

# Round 3: A6=30 again to confirm
log("")
log("=" * 50)
log("ROUND 3: A6 = 30 µL (confirm)")
log("=" * 50)
val = 30 * 10
hi = (val >> 8) & 0xFF
lo = val & 0xFF
r = sr(pkt(0xA6, hi, lo), wait=0.5)
log(f"  A6=30: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Display shows 30? ")
log(f"  >> {note}")
log("")
log("  Dip tip in water.")
log("  PRESS THE PHYSICAL BUTTON.")
note = log_input("  How much water? ")
log(f"  >> {note}")

log("")
log("Was there a clear difference between 30 and 300?")
answer = log_input("Answer: ")
log(f">> {answer}")

ser.close()
log("\nDone.")
_log.close()
