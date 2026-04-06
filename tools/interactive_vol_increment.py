#!/usr/bin/env python3
"""Test B-range commands as volume increment/decrement.

Sends each cmd 3 times in a row to see if the display volume changes
incrementally. Watch the display number.

Run directly:
    python tools/interactive_vol_increment.py
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


def send_recv(ser: serial.Serial, pkt: bytes, wait: float = 0.5) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

resp = send_recv(ser, make_pkt(0xA5))
print(f"Handshake: {resp.hex(' ')}\n")
print("NOTE: Watch the pipette DISPLAY volume number.\n")

candidates = [
    ("B1 b2=0x01 (×3)", 0xB1, 0x01),
    ("B2 b2=0x01 (×3)", 0xB2, 0x01),
    ("B4 b2=0x01 (×3)", 0xB4, 0x01),
    ("B5 b2=0x01 (×3)", 0xB5, 0x01),
    ("B6 b2=0x01 (×3)", 0xB6, 0x01),
    ("B7 b2=0x01 (×3)", 0xB7, 0x01),
    # Also try b2=0x00 which might be the other direction
    ("B1 b2=0x00 (×3)", 0xB1, 0x00),
    ("B2 b2=0x00 (×3)", 0xB2, 0x00),
    ("B4 b2=0x00 (×3)", 0xB4, 0x00),
    ("B5 b2=0x00 (×3)", 0xB5, 0x00),
    ("B6 b2=0x00 (×3)", 0xB6, 0x00),
    ("B7 b2=0x00 (×3)", 0xB7, 0x00),
    # Try with larger b2 as step size?
    ("B1 b2=0x0A (×3, step=10?)", 0xB1, 0x0A),
    ("B2 b2=0x0A (×3, step=10?)", 0xB2, 0x0A),
]

for i, (label, cmd, b2) in enumerate(candidates):
    print(f"--- [{i+1}/{len(candidates)}] {label} ---")
    ans = input("Press ENTER to send 3× (or 'q' to quit): ")
    if ans.strip().lower() == "q":
        break
    for rep in range(3):
        pkt = make_pkt(cmd, b2)
        resp = send_recv(ser, pkt, wait=0.3)
        rx = resp.hex(" ") if resp else "(none)"
        print(f"  [{rep+1}] TX: {pkt.hex(' ')}  RX: {rx}")
    note = input("  Display change after 3 sends? ")
    print(f"  >> {note}\n")

ser.close()
print("Done.")
