#!/usr/bin/env python3
"""Find the dispense command. We know B3=aspirate.

Test B0, B1, B2, B4, B5, B6, B7 one at a time to find which
pushes the piston back down (dispense).
"""

import time

import serial

HEADER_TX = 0xFE
PORT = "/dev/cu.usbserial-0001"


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(cmd: int, b2: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, cmd, b2, 0x00, 0x00])
    return pkt + bytes([checksum(pkt)])


def send_recv(ser: serial.Serial, pkt: bytes) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(3.0)
    return ser.read(64)


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

# Handshake
resp = send_recv(ser, make_pkt(0xA5))
print(f"Handshake: {resp.hex(' ')}")
time.sleep(1.0)

candidates = [
    ("B0 b2=0x01", 0xB0, 0x01),
    ("B0 b2=0x00", 0xB0, 0x00),
    ("B1 b2=0x01", 0xB1, 0x01),
    ("B1 b2=0x00", 0xB1, 0x00),
    ("B2 b2=0x01", 0xB2, 0x01),
    ("B2 b2=0x00", 0xB2, 0x00),
    ("B4 b2=0x01", 0xB4, 0x01),
    ("B4 b2=0x00", 0xB4, 0x00),
    ("B5 b2=0x01", 0xB5, 0x01),
    ("B5 b2=0x00", 0xB5, 0x00),
    ("B6 b2=0x01", 0xB6, 0x01),
    ("B6 b2=0x00", 0xB6, 0x00),
    ("B7 b2=0x01", 0xB7, 0x01),
    ("B7 b2=0x00", 0xB7, 0x00),
]

for i, (label, cmd, b2) in enumerate(candidates):
    print(f"\n{'=' * 50}")
    print(f"[{i + 1}/{len(candidates)}] >>> {label}")
    print("    WATCH FOR DISPENSE (piston pushes down)")
    print(f"{'=' * 50}")
    time.sleep(3.0)
    pkt = make_pkt(cmd, b2)
    print(f"TX: {pkt.hex(' ')}")
    resp = send_recv(ser, pkt)
    rx = resp.hex(" ") if resp else "(none)"
    double = " ** DOUBLE RESPONSE **" if len(resp) > 6 else ""
    print(f"RX ({len(resp)}b): {rx}{double}")
    time.sleep(5.0)

ser.close()
print("\nDone.")
