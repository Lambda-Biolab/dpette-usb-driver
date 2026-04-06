#!/usr/bin/env python3
"""Test if SendCaliVolume (A6) changes the aspirate volume.

Theory: A6 sets the motor travel distance, then B3 aspirates at that distance.
We'll send A6 with a VERY different volume from the display, then aspirate.

If the aspirated amount changes, A6 IS the volume setter.

Run directly — watch how much the pipette draws.
    python tools/test_a6_then_aspirate.py
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
print(f"Handshake: {resp.hex(' ')}\n")

tests = [
    ("Control: aspirate at DISPLAY volume (no A6 sent)", None),
    ("A6=30uL then aspirate", 30),
    ("A6=150uL then aspirate", 150),
    ("A6=300uL then aspirate", 300),
    ("Control again: aspirate without A6", None),
]

for i, (label, vol) in enumerate(tests):
    print(f"--- [{i+1}/{len(tests)}] {label} ---")
    input("Press ENTER (watch how much it draws): ")

    if vol is not None:
        pkt = vol_pkt(vol)
        resp = send_recv(ser, pkt, wait=0.5)
        print(f"  A6 vol={vol}uL: TX {pkt.hex(' ')} → RX {resp.hex(' ')}")

    # Aspirate
    pkt = make_pkt(0xB3, 0x01)
    resp = send_recv(ser, pkt, wait=3.0)
    print(f"  Aspirate:   TX {pkt.hex(' ')} → RX ({len(resp)}b) {resp.hex(' ')}")

    note = input("  How much did it draw? ")
    print(f"  >> {note}")

    # Dispense to reset
    print("  (dispensing to reset)")
    pkt = make_pkt(0xB0, 0x01)
    resp = send_recv(ser, pkt, wait=2.0)
    print(f"  Dispense:   RX ({len(resp)}b) {resp.hex(' ')}\n")

ser.close()
print("Done.")
