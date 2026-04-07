#!/usr/bin/env python3
"""Explore calibration mode carefully.

Enters calibration mode, sends A6, then LISTENS — no B3 aspirate.
Watch the pipette display and report what happens at each step.

Run directly:
    python tools/test_cali_mode.py
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

print("=== CALIBRATION MODE EXPLORATION ===")
print("Watch the pipette display carefully at each step.\n")

# Step 1: Handshake
input("[1] Press ENTER to send Handshake (A5 b2=0): ")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Display shows? ")
print(f"    >> {note}\n")

# Step 2: StartCalibrate
input("[2] Press ENTER to send StartCalibrate (A5 b2=1): ")
resp = send_recv(ser, make_pkt(0xA5, 0x01))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Display changed? Describe what you see: ")
print(f"    >> {note}\n")

# Step 3: Listen for 5 seconds
print("[3] Listening for 5 seconds for any async data...")
time.sleep(0.5)
ser.reset_input_buffer()
time.sleep(5.0)
data = ser.read(256)
if data:
    print(f"    Received ({len(data)}b): {data.hex(' ')}")
else:
    print("    (no data received)")
note = input("    Anything happen on the display? ")
print(f"    >> {note}\n")

# Step 4: SendCaliVolume = 50 µL
input("[4] Press ENTER to send A6=50uL: ")
resp = send_recv(ser, vol_pkt(50), wait=1.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Display changed? Any motor movement? ")
print(f"    >> {note}\n")

# Step 5: Listen again
print("[5] Listening for 5 seconds...")
ser.reset_input_buffer()
time.sleep(5.0)
data = ser.read(256)
if data:
    print(f"    Received ({len(data)}b): {data.hex(' ')}")
else:
    print("    (no data received)")
note = input("    Anything happen? ")
print(f"    >> {note}\n")

# Step 6: Try reading state in calibration mode
print("[6] Reading A1/A2 in calibration mode...")
resp = send_recv(ser, make_pkt(0xA1), wait=0.5)
print(f"    A1: ({len(resp):2d}b) {resp.hex(' ') if resp else '(none)'}")
resp = send_recv(ser, make_pkt(0xA2), wait=0.5)
print(f"    A2: ({len(resp):2d}b) {resp.hex(' ') if resp else '(none)'}")
note = input("    Anything different? ")
print(f"    >> {note}\n")

# Step 7: Try A6 with different volume
input("[7] Press ENTER to send A6=150uL: ")
resp = send_recv(ser, vol_pkt(150), wait=1.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Display changed? ")
print(f"    >> {note}\n")

# Step 8: Try sending B3 in calibration mode (carefully)
print("[8] Try B3 aspirate in calibration mode")
input("    Press ENTER to send (watch for errors): ")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"    RX: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = input("    What happened? (aspirate/error/nothing): ")
print(f"    >> {note}\n")

# Step 9: Try A5 b2=0 to exit calibration mode
print("[9] Try exiting calibration mode with A5 b2=0")
input("    Press ENTER: ")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Display back to normal? ")
print(f"    >> {note}\n")

ser.close()
print("Done.")
