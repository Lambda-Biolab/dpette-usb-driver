#!/usr/bin/env python3
"""Test A6 volume setting with display at 300uL (max).

All test volumes are below 300, so if A6 is clamped to display, all should work.
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


def vol_pkt(vol_ul: int) -> bytes:
    val = vol_ul * 10
    return make_pkt(0xA6, (val >> 8) & 0xFF, val & 0xFF)


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
print(f"Handshake: {resp.hex(' ')}")
print("Display should be at 300 µL\n")

tests = [
    ("Control: no A6 (should draw 300)", None),
    ("A6=30uL then aspirate", 30),
    ("A6=150uL then aspirate", 150),
    ("A6=250uL then aspirate", 250),
    ("A6=300uL then aspirate", 300),
    ("Control again: no A6", None),
]

for i, (label, vol) in enumerate(tests):
    print(f"--- [{i + 1}/{len(tests)}] {label} ---")
    input("Press ENTER: ")

    if vol is not None:
        pkt = vol_pkt(vol)
        resp = send_recv(ser, pkt, wait=0.5)
        print(f"  A6 vol={vol}uL: TX {pkt.hex(' ')} → RX {resp.hex(' ')}")

    pkt = make_pkt(0xB3, 0x01)
    resp = send_recv(ser, pkt, wait=3.0)
    print(f"  Aspirate:  RX ({len(resp)}b) {resp.hex(' ')}")

    note = input("  How much did it draw? ")
    print(f"  >> {note}")

    pkt = make_pkt(0xB0, 0x01)
    resp = send_recv(ser, pkt, wait=2.0)
    print(f"  Dispensed. RX ({len(resp)}b) {resp.hex(' ')}\n")

ser.close()
print("Done.")
