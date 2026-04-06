#!/usr/bin/env python3
"""Fresh A6 test — minimal sequence, no extra commands.

Tests multiple hypotheses about when A6 works:
  1. A6 immediately after handshake (no prior aspirate)
  2. A6 after one aspirate
  3. Fresh handshake + A6 again
  4. StartCalibrate (A5 b2=1) then A6 then aspirate

Display should be at 100 µL.
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

print("Display should be at 100 µL\n")

# Test 1: Handshake → A6=30 → Aspirate (no control first)
print("=" * 50)
print("TEST 1: Handshake → A6=30 → Aspirate")
print("  (no prior aspirate)")
input("Press ENTER: ")
resp = send_recv(ser, make_pkt(0xA5))
print(f"  Handshake: {resp.hex(' ')}")
resp = send_recv(ser, vol_pkt(30), wait=0.5)
print(f"  A6=30:     {resp.hex(' ')}")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"  Aspirate:  ({len(resp)}b) {resp.hex(' ')}")
note = input("  How much? ")
print(f"  >> {note}")
send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print("  (dispensed)\n")

# Test 2: A6=50 → Aspirate (same session, second A6)
print("=" * 50)
print("TEST 2: A6=50 → Aspirate (same session)")
input("Press ENTER: ")
resp = send_recv(ser, vol_pkt(50), wait=0.5)
print(f"  A6=50:     {resp.hex(' ')}")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"  Aspirate:  ({len(resp)}b) {resp.hex(' ')}")
note = input("  How much? ")
print(f"  >> {note}")
send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print("  (dispensed)\n")

# Test 3: Fresh handshake → A6=50 → Aspirate
print("=" * 50)
print("TEST 3: FRESH Handshake → A6=50 → Aspirate")
input("Press ENTER: ")
ser.close()
time.sleep(1.0)
ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)
resp = send_recv(ser, make_pkt(0xA5))
print(f"  Handshake: {resp.hex(' ')}")
resp = send_recv(ser, vol_pkt(50), wait=0.5)
print(f"  A6=50:     {resp.hex(' ')}")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"  Aspirate:  ({len(resp)}b) {resp.hex(' ')}")
note = input("  How much? ")
print(f"  >> {note}")
send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print("  (dispensed)\n")

# Test 4: Handshake → StartCalibrate → A6=50 → Aspirate
print("=" * 50)
print("TEST 4: Handshake → StartCalibrate(A5 b2=1) → A6=50 → Aspirate")
input("Press ENTER: ")
ser.close()
time.sleep(1.0)
ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"  Handshake:      {resp.hex(' ')}")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=0.5)
print(f"  StartCalibrate: {resp.hex(' ')}")
resp = send_recv(ser, vol_pkt(50), wait=0.5)
print(f"  A6=50:          {resp.hex(' ')}")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"  Aspirate:       ({len(resp)}b) {resp.hex(' ')}")
note = input("  How much? ")
print(f"  >> {note}")
send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print("  (dispensed)\n")

# Test 5: Control — just aspirate, no A6
print("=" * 50)
print("TEST 5: Control — Handshake → Aspirate (no A6)")
input("Press ENTER: ")
ser.close()
time.sleep(1.0)
ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)
resp = send_recv(ser, make_pkt(0xA5))
print(f"  Handshake: {resp.hex(' ')}")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"  Aspirate:  ({len(resp)}b) {resp.hex(' ')}")
note = input("  How much? ")
print(f"  >> {note}")
send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print("  (dispensed)\n")

ser.close()
print("Done.")
