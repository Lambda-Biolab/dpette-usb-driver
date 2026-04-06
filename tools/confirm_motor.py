#!/usr/bin/env python3
"""Send B3 and B0 with b2=0x01 one at a time, 10s apart.

Watch and listen to the pipette carefully.
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
    time.sleep(2.0)
    return ser.read(64)


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

# Handshake
resp = send_recv(ser, make_pkt(0xA5))
print(f"Handshake: {resp.hex(' ')}")
time.sleep(2.0)

# Test 1: B3 b2=0x01
print("\n" + "=" * 50)
print(">>> Sending B3 b2=0x01 in 3 seconds...")
print("    WATCH THE PIPETTE")
print("=" * 50)
time.sleep(3.0)
pkt = make_pkt(0xB3, 0x01)
print(f"TX: {pkt.hex(' ')}")
resp = send_recv(ser, pkt)
print(f"RX ({len(resp)}b): {resp.hex(' ') if resp else '(none)'}")

# Wait 10 seconds
print("\n... waiting 10 seconds ...\n")
time.sleep(10.0)

# Test 2: B0 b2=0x01
print("=" * 50)
print(">>> Sending B0 b2=0x01 in 3 seconds...")
print("    WATCH THE PIPETTE")
print("=" * 50)
time.sleep(3.0)
pkt = make_pkt(0xB0, 0x01)
print(f"TX: {pkt.hex(' ')}")
resp = send_recv(ser, pkt)
print(f"RX ({len(resp)}b): {resp.hex(' ') if resp else '(none)'}")

# Wait 10 seconds
print("\n... waiting 10 seconds ...\n")
time.sleep(10.0)

# Test 3: B3 again to see if it reverses
print("=" * 50)
print(">>> Sending B3 b2=0x01 AGAIN in 3 seconds...")
print("    WATCH THE PIPETTE")
print("=" * 50)
time.sleep(3.0)
pkt = make_pkt(0xB3, 0x01)
print(f"TX: {pkt.hex(' ')}")
resp = send_recv(ser, pkt)
print(f"RX ({len(resp)}b): {resp.hex(' ') if resp else '(none)'}")

ser.close()
print("\nDone. What did you see?")
