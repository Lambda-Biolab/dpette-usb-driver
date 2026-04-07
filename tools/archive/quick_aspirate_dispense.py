#!/usr/bin/env python3
"""Quick aspirate then dispense — confirm it uses the current display volume."""

import time

import serial

PORT = "/dev/cu.usbserial-0001"
HEADER_TX = 0xFE


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(cmd: int, b2: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, cmd, b2, 0x00, 0x00])
    return pkt + bytes([checksum(pkt)])


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

# Handshake
ser.reset_input_buffer()
ser.write(make_pkt(0xA5))
ser.flush()
time.sleep(1.0)
resp = ser.read(6)
print(f"Handshake: {resp.hex(' ')}")

# Aspirate
print("\nAspirating...")
ser.reset_input_buffer()
ser.write(make_pkt(0xB3, 0x01))
ser.flush()
time.sleep(3.0)
resp = ser.read(64)
print(f"RX ({len(resp)}b): {resp.hex(' ')}")

print("\nWaiting 5s before dispense...")
time.sleep(5.0)

# Dispense
print("Dispensing...")
ser.reset_input_buffer()
ser.write(make_pkt(0xB0, 0x01))
ser.flush()
time.sleep(3.0)
resp = ser.read(64)
print(f"RX ({len(resp)}b): {resp.hex(' ')}")

ser.close()
print("\nDone.")
