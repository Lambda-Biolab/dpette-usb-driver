#!/usr/bin/env python3
"""Stay in calibration mode — set volumes and aspirate without exiting.

Dismiss Err4 before running.

Run directly:
    python tools/test_stay_in_cal.py
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

print("=== STAY IN CAL MODE TEST ===\n")

# Handshake
print("[1] Handshake")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ') if resp else 'FAIL'}")

# Enter cal mode (STAY IN IT)
print("\n[2] Enter cal mode")
input("    Press ENTER: ")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
input("    Dismiss Err4 if needed, press ENTER when cal menu shows: ")

# Now stay in cal mode and test volumes
for vol in [100, 200, 300]:
    print(f"\n{'=' * 50}")
    print(f"SET VOLUME: {vol} µL (staying in cal mode)")
    print(f"{'=' * 50}")

    # Set volume
    resp = send_recv(ser, vol_pkt(vol), wait=0.5)
    print(f"  A6={vol}uL: {resp.hex(' ') if resp else '(none)'}")
    note = input(f"  Does display show {vol}? ")
    print(f"  >> {note}")

    # Try B3 aspirate in cal mode
    print("\n  Trying B3 aspirate...")
    input("  Press ENTER: ")
    resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
    print(f"  B3: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
    b3_ok = len(resp) >= 12
    note = input("  Motor moved? How much? ")
    print(f"  >> {note}")

    # Try B0 dispense in cal mode
    print("\n  Trying B0 dispense...")
    resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
    print(f"  B0: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
    note = input("  Motor moved? ")
    print(f"  >> {note}")

    # If B3 didn't work, try other aspirate triggers
    if not b3_ok:
        print("\n  B3 didn't work — trying alternatives...")

        # Maybe B3 b2=0x00 in cal mode?
        resp = send_recv(ser, make_pkt(0xB3, 0x00), wait=2.0)
        print(f"  B3 b2=0: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")

        # Maybe A3 triggers cal aspirate?
        resp = send_recv(ser, make_pkt(0xA3, 0x01), wait=2.0)
        print(f"  A3 b2=1: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")

        # Maybe re-sending A6 triggers aspirate?
        resp = send_recv(ser, vol_pkt(vol), wait=2.0)
        print(f"  A6 again: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")

        note = input("  Did any of those move the motor? ")
        print(f"  >> {note}")

# Stay in cal mode — don't exit
print("\n" + "=" * 50)
print("Tests complete. Still in cal mode (NOT exiting).")
print("Close this script with Ctrl+C when done.")

try:
    while True:
        time.sleep(1.0)
except KeyboardInterrupt:
    pass

ser.close()
print("\nDone.")
