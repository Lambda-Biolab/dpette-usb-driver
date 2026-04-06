#!/usr/bin/env python3
"""Aspirate/dispense test at dial volume.

Set the volume on the pipette dial before running.
Tip should be on and dipped in water.
DO NOT TOUCH the pipette during the test.

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


def pkt(cmd: int, b2: int = 0) -> bytes:
    data = bytes([0xFE, cmd, b2, 0x00, 0x00])
    return data + bytes([(cmd + b2) & 0xFF])


def sr(p: bytes, wait: float = 1.0) -> bytes:
    ser.reset_input_buffer()
    ser.write(p)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


log("=== ASPIRATE/DISPENSE TEST ===")
log("Tip on, dipped in water, HANDS OFF pipette")
vol = log_input("What volume is the dial set to? ")
log(f">> {vol}\n")

log_input("Press ENTER when tip is in water and hands are off: ")
log("")

# Handshake
r = sr(pkt(0xA5))
log(f"Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

# B0 prime
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"B0 prime:  ({len(r)}b) {r.hex(' ') if r else '(none)'}")

# B3 aspirate
r = sr(pkt(0xB3, 0x01), wait=3.0)
log(f"B3 aspir:  ({len(r)}b) {r.hex(' ') if r else '(none)'}")
ok = len(r) >= 12
log(f"Motor {'OK' if ok else 'REJECTED'}")

if ok:
    note = log_input(f"\nHow much water? (expecting ~{vol}uL): ")
    log(f">> {note}\n")

    log_input("Hold over cup. Press ENTER to dispense: ")
    r = sr(pkt(0xB0, 0x01), wait=2.0)
    log(f"B0 disp:   ({len(r)}b) {r.hex(' ') if r else '(none)'}")

    note = log_input("Dispensed? (yes/no): ")
    log(f">> {note}")

ser.close()
log("\nDone.")
_log.close()
