#!/usr/bin/env python3
"""Exit calibration mode properly, then test aspirate.

Dismiss Err4 on pipette before running this.
"""

import time

import serial

ser = serial.Serial(
    port="/dev/cu.usbserial-0001",
    baudrate=9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=3.0,
)


def pkt(cmd, b2=0):
    data = bytes([0xFE, cmd, b2, 0x00, 0x00])
    return data + bytes([(cmd + b2) & 0xFF])


def sr(p, wait=1.0):
    ser.reset_input_buffer()
    ser.write(p)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


# Step 1: Normal handshake
print("[1] Handshake (A5 b2=0)")
r = sr(pkt(0xA5, 0x00))
print(f"    RX: {r.hex(' ') if r else '(none)'}")

# Step 2: Enter cal mode
print("[2] Enter cal mode (A5 b2=1)")
r = sr(pkt(0xA5, 0x01), wait=2.0)
print(f"    RX: {r.hex(' ') if r else '(none)'}")

# Step 3: Exit cal mode
print("[3] Exit cal mode (A5 b2=0)")
r = sr(pkt(0xA5, 0x00))
print(f"    RX: {r.hex(' ') if r else '(none)'}")

# Step 4: Another handshake to be sure
print("[4] Handshake again")
r = sr(pkt(0xA5, 0x00))
print(f"    RX: {r.hex(' ') if r else '(none)'}")

# Step 5: Test aspirate
print("[5] Aspirate (B3 b2=1)")
r = sr(pkt(0xB3, 0x01), wait=3.0)
print(f"    RX: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
print(f"    Motor {'OK' if len(r) >= 12 else 'REJECTED'}")

if len(r) >= 12:
    print("[6] Dispense")
    r = sr(pkt(0xB0, 0x01), wait=2.0)
    print(f"    RX: {r.hex(' ') if r else '(none)'}")

ser.close()
print("Done.")
