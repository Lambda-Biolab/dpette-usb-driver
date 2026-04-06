#!/usr/bin/env python3
"""Test if A6 volume persists after exiting calibration mode.

Flow:
  1. Handshake + dispense (reset piston from any prior state)
  2. Enter cal mode (A5 b2=1)
  3. Set volume to 50 µL with A6
  4. Exit cal mode (A5 b2=0)
  5. Check display — does it show 50?
  6. Aspirate with B3 — does it draw 50?

Run directly:
    python tools/test_cali_volume_persist.py
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

print("=== CALIBRATION MODE VOLUME PERSISTENCE TEST ===\n")
print("What volume does the display show right now?")
input("Type it and press ENTER: ")

# Step 1: Handshake
print("\n[1] Handshake")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")

# Step 1b: Dispense to reset piston
print("[1b] Dispense to reset piston")
resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
time.sleep(1.0)

# Step 2: Enter calibration mode
print("\n[2] Entering calibration mode (A5 b2=1)")
print("    WARNING: This may auto-aspirate and beep.")
input("    Press ENTER when ready: ")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    What happened? (describe display + any motor/beep): ")
print(f"    >> {note}\n")

# Step 2b: Wait and drain any error beep
time.sleep(2.0)

# Step 3: Set volume to 50
print("[3] Setting volume to 50 µL (A6)")
resp = send_recv(ser, vol_pkt(50), wait=1.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Does display show 50? ")
print(f"    >> {note}\n")

# Step 4: Dispense in cal mode (try to reset piston)
print("[4] Dispense in cal mode (B0 b2=1)")
resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Motor moved? ")
print(f"    >> {note}\n")

# Step 5: Exit calibration mode
print("[5] Exiting calibration mode (A5 b2=0)")
input("    Press ENTER: ")
resp = send_recv(ser, make_pkt(0xA5, 0x00), wait=1.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
note = input("    Display? Error? What volume shown? ")
print(f"    >> {note}\n")

# Step 5b: If error, wait for user to clear it
input("[5b] If there's an error, clear it with the button. Press ENTER when normal: ")

# Step 6: Check display
note = input("\n[6] What volume does the display show NOW? ")
print(f"    >> {note}\n")

# Step 7: Aspirate with B3
print("[7] Aspirate with B3")
input("    Press ENTER to aspirate: ")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"    RX: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = input("    How much did it draw? ")
print(f"    >> {note}\n")

# Step 8: Dispense
print("[8] Dispense")
resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")

ser.close()
print("\nDone.")
