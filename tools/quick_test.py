#!/usr/bin/env python3
"""Explore B0 b2=1,2,3 in cal mode at different A6 volumes.

Does B0 b2=2 or b2=3 aspirate at A6 volume?
Test each at A6=30 and A6=300.

Must dismiss Err4 first.
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


log("=== B0 b2=1/2/3 AT DIFFERENT A6 VOLUMES ===")
log("If amount changes with A6, we have serial volume control!")
log("")

log_input("[1] Dismiss Err4, press ENTER: ")
r = sr(pkt(0xA5), wait=1.0)
log(f"  Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

log("[2] Entering cal mode...")
r = sr(pkt(0xA5, 0x01), wait=3.0)
log(f"  A5 b2=1: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log_input("  Dismiss Err4, wait for homing to FULLY finish. Press ENTER: ")
time.sleep(10.0)
log("  Settled.")
log("")

for b2_val in [1, 2, 3]:
    for vol in [30, 300]:
        log(f"{'=' * 50}")
        log(f"B0 b2={b2_val} at A6={vol} µL")
        log(f"{'=' * 50}")

        val = vol * 10
        r = sr(pkt(0xA6, (val >> 8) & 0xFF, val & 0xFF), wait=0.5)
        log(f"  A6={vol}: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

        log_input("  Tip in water, HANDS OFF. Press ENTER: ")
        p = pkt(0xB0, b2_val)
        r = sr(p, wait=3.0)
        log(f"  TX: {p.hex(' ')}")
        log(f"  RX: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
        note = log_input(f"  How much water? (A6={vol}, b2={b2_val}): ")
        log(f"  >> {note}")
        log("")

log("Summary: did ANY b2 value show different amounts at 30 vs 300?")
answer = log_input("Answer: ")
log(f">> {answer}")

ser.close()
log("\nDone.")
_log.close()
