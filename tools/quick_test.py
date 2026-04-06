#!/usr/bin/env python3
"""Extreme volume test — 30 vs 300 µL for clear visual difference.

Primes once at the start, then aspirates at each volume.
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


log("=== EXTREME VOLUME TEST (30 vs 300 µL) ===")
log("We prime ONCE, then test each volume.")
log("The difference between 30 and 300 should be unmistakable.")
log("")

# Initial handshake + prime
log("Initial setup:")
r = sr(pkt(0xA5))
log(f"  Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
r = sr(pkt(0xB0, 0x01), wait=2.0)
log(f"  B0 prime:  ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log("  (prime done — no more B0 before aspirates)")
log("")

for vol in [300, 30, 300]:
    log(f"{'=' * 50}")
    log(f"TEST: dial = {vol} µL")
    log(f"{'=' * 50}")
    log_input(f"Set dial to {vol}, tip in water, HANDS OFF. Press ENTER: ")
    log("")

    # B3 aspirate only — no B0 prime (already primed)
    r = sr(pkt(0xB3, 0x01), wait=3.0)
    log(f"  B3 aspir:  ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    ok = len(r) >= 12
    log(f"  Motor {'OK' if ok else 'REJECTED'}")

    if ok:
        amount = log_input(f"  How much water in tip? (dial={vol}): ")
        log(f"  >> {amount}")
    else:
        log("  REJECTED — sending B0 prime and retrying")
        r = sr(pkt(0xB0, 0x01), wait=2.0)
        log(f"  B0 prime: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
        r = sr(pkt(0xB3, 0x01), wait=3.0)
        log(f"  B3 retry: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
        ok = len(r) >= 12
        log(f"  Motor {'OK' if ok else 'STILL REJECTED'}")
        if ok:
            amount = log_input(f"  How much water in tip? (dial={vol}): ")
            log(f"  >> {amount}")

    # Dispense
    log_input("  Hold over cup, press ENTER to dispense: ")
    r = sr(pkt(0xB0, 0x01), wait=2.0)
    log(f"  B0 disp:  ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    log("")

ser.close()
log("Done. Was there a clear difference between 30 and 300?")
log_input("Answer: ")
log("")
_log.close()
