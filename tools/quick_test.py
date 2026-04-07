#!/usr/bin/env python3
"""Full CMD scan in cal mode with b2=0x00 (expert Q3).

Previous scan used b2=0x01. Some commands behave differently at b2=0x00.
Also tests b2=0x02, 0x03, 0xFF for responding commands.

Must dismiss Err4 first. WATCH FOR MOTOR.
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
    timeout=0.5,
)


def pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    ck = (cmd + b2 + b3 + b4) & 0xFF
    return bytes([0xFE, cmd, b2, b3, b4, ck])


def sr(p: bytes, wait: float = 0.3) -> bytes:
    ser.reset_input_buffer()
    ser.write(p)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


log("=== CMD SCAN b2=0x00 IN CAL MODE ===")
log("WATCH FOR MOTOR MOVEMENT!")
log("")

# Setup
log_input("[Setup] Dismiss Err4, press ENTER: ")
ser.timeout = 3.0
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

ser.timeout = 0.5

# Scan 1: all 256 CMDs with b2=0x00
log("SCAN 1: 0x00-0xFF with b2=0x00 (skipping A5)")
log("Responding commands:")
known_b1 = {}  # store b2=0x01 responses for comparison
for cmd in range(256):
    if cmd == 0xA5:
        continue
    r = sr(pkt(cmd, 0x00), wait=0.1)
    if r:
        log(f"  0x{cmd:02X} b2=00: ({len(r)}b) {r.hex(' ')}")

log("")
log_input("Did ANY motor movement happen during scan 1? ")
log("")

# Scan 2: responding commands with b2=0x02, 0x03, 0xFF
log("SCAN 2: Known responding CMDs with b2=0x02, 0x03, 0xFF")
responding = [
    0xA0,
    0xA1,
    0xA2,
    0xA3,
    0xA4,
    0xA6,
    0xA7,
    0xA8,
    0xB0,
    0xB1,
    0xB2,
    0xB3,
    0xB4,
    0xB5,
    0xB6,
    0xB7,
]

for b2 in [0x02, 0x03, 0xFF]:
    log(f"  --- b2=0x{b2:02X} ---")
    for cmd in responding:
        r = sr(pkt(cmd, b2), wait=0.15)
        if r:
            log(f"    0x{cmd:02X}: ({len(r)}b) {r.hex(' ')}")

log("")
log_input("Did ANY motor movement happen during scan 2? ")

ser.close()
log("\nDone.")
_log.close()
