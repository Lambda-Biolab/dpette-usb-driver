#!/usr/bin/env python3
"""Test if changing k coefficient in EEPROM changes aspiration volume.

Reads current k, writes a modified k, aspirates, then RESTORES original.
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


def read_ee(addr: int) -> int:
    r = sr(pkt(0xA3, 0x00, addr), wait=0.3)
    return r[2] if len(r) >= 3 else -1


def write_ee(addr: int, val: int) -> None:
    sr(pkt(0xA4, 0x00, addr, val), wait=0.3)


log("=== EEPROM K COEFFICIENT VOLUME TEST ===")
log("Dial should be at 300. HANDS OFF during aspirate.")
log("We will modify k, aspirate, then RESTORE original k.")
log("")

dial = log_input("What volume is the dial set to? ")

# Handshake + prime
sr(pkt(0xA5), wait=1.0)
sr(pkt(0xB0, 0x01), wait=2.0)
log("Handshake + prime done")

# Read current k (4 bytes at 0x90-0x93) and b (4 bytes at 0x94-0x97)
# Also seg2 at 0x98-0x9B, 0x9C-0x9F
log("")
log("Reading current calibration:")
orig = {}
for addr in range(0x90, 0xA0):
    val = read_ee(addr)
    orig[addr] = val
    log(f"  0x{addr:02X}: 0x{val:02X}")

log("")

# TEST 1: Baseline aspirate with original k
log_input("TEST 1: Baseline with original k. Tip in water, ENTER: ")
r = sr(pkt(0xB3, 0x01), wait=3.0)
ok = len(r) >= 12
log(f"  B3: ({len(r)}b) Motor {'OK' if ok else 'REJECTED'}")
if ok:
    amount = log_input(f"  How much water? (dial={dial}): ")
    log(f"  >> {amount}")
    log_input("  Dispense. Press ENTER: ")
    sr(pkt(0xB0, 0x01), wait=2.0)
    log("  Dispensed")
log("")

# MODIFY K: halve the k value
# k is stored as 4 bytes at 0x90-0x93 (little-endian)
# Current: 0x00, 0x00, 0x2F, 0xC7
# As u32 LE: 0xC72F0000 = 3341107200
# Half: 0x63970000 → bytes: 0x00, 0x00, 0x97, 0x63
# Actually simpler: just halve byte[3] (0xC7 → 0x63)
log("Modifying k: halving byte[3] (0xC7 → 0x63)")
log("Writing to BOTH seg1 (0x93) and seg2 (0x9B)")
write_ee(0x93, 0x63)
write_ee(0x9B, 0x63)

# Verify
v1 = read_ee(0x93)
v2 = read_ee(0x9B)
log(f"  0x93 now: 0x{v1:02X} (was 0xC7)")
log(f"  0x9B now: 0x{v2:02X} (was 0xC7)")
log("")

# TEST 2: Aspirate with halved k
log_input("TEST 2: Aspirate with HALVED k. Tip in water, ENTER: ")
r = sr(pkt(0xB3, 0x01), wait=3.0)
ok = len(r) >= 12
log(f"  B3: ({len(r)}b) Motor {'OK' if ok else 'REJECTED'}")
if ok:
    amount = log_input(f"  How much water? (should be ~half of {dial}): ")
    log(f"  >> {amount}")
    log_input("  Dispense. Press ENTER: ")
    sr(pkt(0xB0, 0x01), wait=2.0)
    log("  Dispensed")
log("")

# RESTORE original k
log("Restoring original k values...")
for addr in range(0x90, 0xA0):
    write_ee(addr, orig[addr])

# Verify restore
log("Verifying restore:")
for addr in range(0x90, 0xA0):
    val = read_ee(addr)
    match = "OK" if val == orig[addr] else f"MISMATCH (got 0x{val:02X})"
    log(f"  0x{addr:02X}: 0x{val:02X} {match}")
log("")

# TEST 3: Aspirate with restored k (should be back to normal)
log_input("TEST 3: Aspirate with RESTORED k. Tip in water, ENTER: ")
r = sr(pkt(0xB3, 0x01), wait=3.0)
ok = len(r) >= 12
log(f"  B3: ({len(r)}b) Motor {'OK' if ok else 'REJECTED'}")
if ok:
    amount = log_input(f"  How much water? (should be back to ~{dial}): ")
    log(f"  >> {amount}")
    log_input("  Dispense. Press ENTER: ")
    sr(pkt(0xB0, 0x01), wait=2.0)
    log("  Dispensed")

ser.close()
log("\nDone.")
_log.close()
