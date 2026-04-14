#!/usr/bin/env python3
"""Interactive test of B1-B7 with volume-like payloads.

Tries encoding volumes as big-endian × 10 in b2/b3.
Watch the pipette DISPLAY for volume changes.

Run directly:
    python tools/interactive_volume.py
"""

import time

import serial

HEADER_TX = 0xFE
PORT = "/dev/cu.usbserial-0001"


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, cmd, b2, b3, b4])
    return pkt + bytes([checksum(pkt)])


def vol_encode(volume_ul: int) -> tuple[int, int]:
    """Encode volume as big-endian × 10."""
    val = volume_ul * 10
    return (val >> 8) & 0xFF, val & 0xFF


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

ser.reset_input_buffer()
ser.write(make_pkt(0xA5))
ser.flush()
time.sleep(1.0)
resp = ser.read(6)
print(f"Handshake: {resp.hex(' ')}\n")

# 300 µL pipette — test with 150 µL (within range, different from current)
vol = 150
hi, lo = vol_encode(vol)
print(f"Test volume: {vol} µL → encoded ×10: 0x{hi:02X} 0x{lo:02X}")
print("This is a 30-300 µL pipette. Watch the DISPLAY for changes.\n")

probes = [
    # Try volume in b2/b3 (like SendCaliVolume encoding: ×10 big-endian)
    (f"B1 vol={vol}uL (×10 in b2/b3)", 0xB1, hi, lo, 0x00),
    (f"B2 vol={vol}uL (×10 in b2/b3)", 0xB2, hi, lo, 0x00),
    (f"B4 vol={vol}uL (×10 in b2/b3)", 0xB4, hi, lo, 0x00),
    (f"B5 vol={vol}uL (×10 in b2/b3)", 0xB5, hi, lo, 0x00),
    (f"B6 vol={vol}uL (×10 in b2/b3)", 0xB6, hi, lo, 0x00),
    (f"B7 vol={vol}uL (×10 in b2/b3)", 0xB7, hi, lo, 0x00),
    # Try with b4=0x01 (trigger flag?)
    (f"B1 vol={vol}uL b4=1", 0xB1, hi, lo, 0x01),
    (f"B2 vol={vol}uL b4=1", 0xB2, hi, lo, 0x01),
    (f"B4 vol={vol}uL b4=1", 0xB4, hi, lo, 0x01),
    (f"B5 vol={vol}uL b4=1", 0xB5, hi, lo, 0x01),
    # Try raw volume (not ×10) in b2/b3
    (f"B1 raw {vol} in b2/b3", 0xB1, (vol >> 8) & 0xFF, vol & 0xFF, 0x00),
    (f"B2 raw {vol} in b2/b3", 0xB2, (vol >> 8) & 0xFF, vol & 0xFF, 0x00),
    # Try A7 with volume
    (f"A7 vol={vol}uL", 0xA7, hi, lo, 0x00),
]

for i, (label, cmd, b2, b3, b4) in enumerate(probes):
    print(f"--- [{i + 1}/{len(probes)}] {label} ---")
    ans = input("Press ENTER to send (or 'q' to quit): ")
    if ans.strip().lower() == "q":
        break
    pkt = make_pkt(cmd, b2, b3, b4)
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(1.0)
    resp = ser.read(64)
    rx = resp.hex(" ") if resp else "(none)"
    print(f"  TX: {pkt.hex(' ')}")
    print(f"  RX ({len(resp):2d}b): {rx}")
    note = input("  Display change? (nothing/volume changed/other): ")
    print(f"  >> {note}\n")

ser.close()
print("Done.")
