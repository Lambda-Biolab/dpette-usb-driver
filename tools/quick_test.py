#!/usr/bin/env python3
"""Test post-button-aspirate state in cal mode.

Q1: After physical button aspirate, what commands work?
Q2: Can B0 dispense? Does B3 work? Is device in cal or normal mode?

Logs to captures/live_log.txt
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


log("=== POST-BUTTON-ASPIRATE STATE TEST ===")
log("")

# Setup: enter cal mode, set A6=300
log_input("[Setup] Dismiss Err4, press ENTER: ")
r = sr(pkt(0xA5), wait=1.0)
log(f"  Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
r = sr(pkt(0xA5, 0x01), wait=3.0)
log(f"  Enter cal: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log_input("  Dismiss Err4, wait for homing. Press ENTER: ")
time.sleep(5.0)

val = 300 * 10
r = sr(pkt(0xA6, (val >> 8) & 0xFF, val & 0xFF), wait=0.5)
log(f"  A6=300: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log("")

# Step 1: Physical button aspirate
log("=" * 50)
log("STEP 1: Press the PHYSICAL BUTTON to aspirate")
log("(tip in water, A6 is set to 300)")
log("=" * 50)
log_input("Press the button now, then press ENTER here: ")
note = log_input("  Did it aspirate? How much? ")
log(f"  >> {note}")
log("")

# Step 2: Check serial state immediately after button aspirate
log("=" * 50)
log("STEP 2: Check serial commands after button aspirate")
log("=" * 50)

# Try B0 dispense
log("  Trying B0 dispense...")
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"  B0: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Did B0 dispense? ")
log(f"  >> {note}")

# Try B3 aspirate
log("  Trying B3 aspirate...")
r = sr(pkt(0xB3, 0x01), wait=2.0)
ok = len(r) >= 12
log(
    f"  B3: ({len(r)}b) {r.hex(' ') if r else '(none)'}  Motor {'OK' if ok else 'REJECTED'}"
)
note = log_input("  Did B3 work? ")
log(f"  >> {note}")

# Try A6 to change volume
log("  Trying A6=30...")
val2 = 30 * 10
r = sr(pkt(0xA6, (val2 >> 8) & 0xFF, val2 & 0xFF), wait=0.5)
log(f"  A6=30: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Display changed to 30? ")
log(f"  >> {note}")
log("")

# Step 3: Second button aspirate at new volume
log("=" * 50)
log("STEP 3: Press button again (A6 now 30)")
log("=" * 50)
log_input("Tip in water, press button, then ENTER: ")
note = log_input("  How much? (should be ~30 if A6 works): ")
log(f"  >> {note}")
log("")

# Step 4: Can we do a full cycle? A6→button→B0→A6→button
log("=" * 50)
log("STEP 4: Full cycle — A6=300→button→B0→A6=100→button")
log("=" * 50)

val3 = 300 * 10
r = sr(pkt(0xA6, (val3 >> 8) & 0xFF, val3 & 0xFF), wait=0.5)
log(f"  A6=300: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log_input("  Tip in water, press button to aspirate, then ENTER: ")
note = log_input("  How much? ")
log(f"  >> aspirate 300: {note}")

log("  B0 dispense...")
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"  B0: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Dispensed? ")
log(f"  >> dispense: {note}")

val4 = 100 * 10
r = sr(pkt(0xA6, (val4 >> 8) & 0xFF, val4 & 0xFF), wait=0.5)
log(f"  A6=100: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log_input("  Tip in water, press button to aspirate, then ENTER: ")
note = log_input("  How much? (should be ~100): ")
log(f"  >> aspirate 100: {note}")

log("  B0 dispense...")
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"  B0: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
note = log_input("  Dispensed? ")
log(f"  >> dispense: {note}")

log("")
log("SUMMARY: Does the full cycle work?")
log("A6 set volume → button aspirate → B0 dispense → repeat")
answer = log_input("Answer: ")
log(f">> {answer}")

ser.close()
log("\nDone.")
_log.close()
