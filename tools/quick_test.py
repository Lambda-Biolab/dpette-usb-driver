#!/usr/bin/env python3
"""Interactive: isolate which prime+B3 moves motor in cal mode.

Each command waits for your observation before continuing.
Must already be in cal mode with A6 volume set.

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


log("=== ISOLATE MOTOR MOVEMENT: ONE AT A TIME ===")
log("Must be in cal mode with A6 volume set.")
log("Each step: sends PRIME, waits, then sends B3.")
log("You observe motor between each command.")
log("")

# Setup
log_input("[1] Dismiss Err4, press ENTER: ")
r = sr(pkt(0xA5), wait=1.0)
log(f"  Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

log("[2] Entering cal mode...")
r = sr(pkt(0xA5, 0x01), wait=3.0)
log(f"  A5 b2=1: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log_input("  Dismiss Err4, wait for homing. Press ENTER: ")
time.sleep(3.0)

log("[3] A6=100 µL")
val = 100 * 10
r = sr(pkt(0xA6, (val >> 8) & 0xFF, val & 0xFF), wait=0.5)
log(f"  A6: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
log("")

primes = [
    ("B0 b2=1", 0xB0, 0x01),
    ("B1 b2=1", 0xB1, 0x01),
    ("B2 b2=1", 0xB2, 0x01),
    ("B3 b2=1", 0xB3, 0x01),
    ("B4 b2=1", 0xB4, 0x01),
    ("B5 b2=1", 0xB5, 0x01),
    ("B6 b2=1", 0xB6, 0x01),
    ("B7 b2=1", 0xB7, 0x01),
    ("B0 b2=0", 0xB0, 0x00),
    ("B1 b2=0", 0xB1, 0x00),
    ("B2 b2=0", 0xB2, 0x00),
    ("B3 b2=0", 0xB3, 0x00),
    ("B4 b2=0", 0xB4, 0x00),
    ("B5 b2=0", 0xB5, 0x00),
    ("B6 b2=0", 0xB6, 0x00),
    ("B7 b2=0", 0xB7, 0x00),
    ("A0 b2=0", 0xA0, 0x00),
    ("A0 b2=1", 0xA0, 0x01),
    ("A3 b2=0", 0xA3, 0x00),
    ("A3 b2=1", 0xA3, 0x01),
    ("A4 b2=0", 0xA4, 0x00),
    ("A4 b2=1", 0xA4, 0x01),
    ("A6 b2=0", 0xA6, 0x00),
    ("A6 b2=1", 0xA6, 0x01),
    ("A7 b2=0", 0xA7, 0x00),
    ("A7 b2=1", 0xA7, 0x01),
]

for i, (label, cmd, b2) in enumerate(primes):
    log(f"--- [{i+1}/{len(primes)}] PRIME: {label} ---")
    log_input("  Press ENTER to send prime: ")
    p = pkt(cmd, b2)
    r = sr(p, wait=1.0)
    log(f"  Prime TX: {p.hex(' ')}")
    log(f"  Prime RX: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    prime_note = log_input("  Motor moved on PRIME? (yes/no): ")
    log(f"  >> prime: {prime_note}")

    log_input("  Press ENTER to send B3: ")
    r = sr(pkt(0xB3, 0x01), wait=2.0)
    ok = len(r) >= 12
    log(f"  B3 RX: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    log(f"  B3 Motor {'OK <<<' if ok else 'rejected'}")
    b3_note = log_input("  Motor moved on B3? (yes/no): ")
    log(f"  >> B3: {b3_note}")
    log("")

ser.close()
log("Done.")
_log.close()
