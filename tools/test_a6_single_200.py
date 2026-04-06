#!/usr/bin/env python3
"""Single A6 test after fresh reboot — set 200 µL, aspirate once.

Run directly:
    python tools/test_a6_single_200.py
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

print("=== SINGLE VOLUME TEST: A6=200 µL ===\n")

note = input("What volume does the display show? ")
print(f">> {note}\n")

# Handshake
print("[1] Handshake")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ')}")

# Enter cal mode
print("\n[2] Enter cal mode")
input("    Press ENTER: ")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
input("    Clear Err4 with button, then press ENTER: ")

# Set volume to 200
print("\n[3] Set volume to 200 µL")
resp = send_recv(ser, vol_pkt(200), wait=0.5)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Does display show 200? ")
print(f"    >> {note}")

# Exit cal mode
print("\n[4] Exit cal mode")
resp = send_recv(ser, make_pkt(0xA5, 0x00), wait=1.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
input("    Clear any error, then press ENTER: ")

# Re-handshake
print("\n[5] Re-handshake")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ')}")

# Aspirate
print("\n[6] Aspirate — should draw ~200 µL")
input("    Press ENTER: ")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"    RX: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = input("    How much did it draw? ")
print(f"    >> {note}")

# Dispense
print("\n[7] Dispense")
resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")

ser.close()
print("\nDone.")
