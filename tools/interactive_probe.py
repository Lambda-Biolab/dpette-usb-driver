#!/usr/bin/env python3
"""Interactive motor probe — sends one command, waits for your input.

Run this directly in your terminal:
    python tools/interactive_probe.py
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


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

ser.reset_input_buffer()
ser.write(make_pkt(0xA5))
ser.flush()
time.sleep(1.0)
resp = ser.read(6)
print(f"Handshake: {resp.hex(' ')}\n")

cmds = [
    ("B3 b2=1  (ASPIRATE - confirmed)", 0xB3, 0x01),
    ("B0 b2=1  (dispense?)", 0xB0, 0x01),
    ("B0 b2=0", 0xB0, 0x00),
    ("B1 b2=1", 0xB1, 0x01),
    ("B2 b2=1", 0xB2, 0x01),
    ("B4 b2=1", 0xB4, 0x01),
    ("B5 b2=1", 0xB5, 0x01),
    ("B6 b2=1", 0xB6, 0x01),
    ("B7 b2=1", 0xB7, 0x01),
]

for i, (label, cmd, b2) in enumerate(cmds):
    print(f"--- [{i + 1}/{len(cmds)}] {label} ---")
    ans = input("Press ENTER to send (or 'q' to quit): ")
    if ans.strip().lower() == "q":
        break
    pkt = make_pkt(cmd, b2)
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(2.0)
    resp = ser.read(64)
    rx = resp.hex(" ") if resp else "(none)"
    print(f"  TX: {pkt.hex(' ')}")
    print(f"  RX ({len(resp):2d}b): {rx}")
    note = input("  What happened? (nothing/sound/aspirate/dispense/other): ")
    print(f"  >> Logged: {note}\n")

ser.close()
print("Done.")
