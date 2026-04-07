#!/usr/bin/env python3
"""Full flow test: connect, set volume via cal mode, aspirate, dispense.

Tests the complete sequence at 100, 200, and 300 µL.
Dismiss Err4 on pipette before running.

Run directly:
    python tools/test_full_flow.py
"""

import sys
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


def connect_and_clear(ser: serial.Serial) -> bool:
    """Handshake + cal mode toggle to clear stale state."""
    resp = send_recv(ser, make_pkt(0xA5, 0x00))
    if not resp:
        print("  Handshake FAILED")
        return False
    print(f"  Handshake: {resp.hex(' ')}")
    # Enter cal mode
    ser.reset_input_buffer()
    ser.write(make_pkt(0xA5, 0x01))
    ser.flush()
    time.sleep(2.0)
    ser.read(64)  # consume response or timeout
    # Exit cal mode
    resp = send_recv(ser, make_pkt(0xA5, 0x00))
    print(f"  Cal toggle done: {resp.hex(' ') if resp else '(none)'}")
    return True


def set_volume(ser: serial.Serial, vol_ul: int) -> None:
    """Enter cal mode, set volume with A6, exit cal mode."""
    # Enter cal mode
    ser.reset_input_buffer()
    ser.write(make_pkt(0xA5, 0x01))
    ser.flush()
    time.sleep(2.0)
    ser.read(64)
    # Set volume
    resp = send_recv(ser, vol_pkt(vol_ul), wait=0.5)
    print(f"  A6={vol_ul}uL: {resp.hex(' ') if resp else '(none)'}")
    # Exit cal mode
    resp = send_recv(ser, make_pkt(0xA5, 0x00))
    print(f"  Exit cal: {resp.hex(' ') if resp else '(none)'}")
    # Re-handshake
    resp = send_recv(ser, make_pkt(0xA5, 0x00))


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

print("=== FULL FLOW TEST: VOLUME CONTROL + ASPIRATE/DISPENSE ===")
print("Dismiss Err4 on pipette first!\n")

# Initial connect
print("[Connect]")
if not connect_and_clear(ser):
    ser.close()
    sys.exit(1)

# Test each volume
for vol in [100, 200, 300]:
    print(f"\n{'=' * 50}")
    print(f"TEST: {vol} µL")
    print(f"{'=' * 50}")

    print(f"\n[Set volume to {vol} µL]")
    set_volume(ser, vol)

    input(f"\n[Aspirate {vol} µL] Press ENTER: ")
    resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
    print(f"  RX: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
    motor_ok = len(resp) >= 12
    print(f"  Motor {'OK' if motor_ok else 'REJECTED'}")

    if motor_ok:
        note = input(f"  How much did it draw? (expecting ~{vol}): ")
        print(f"  >> {note}")

        print("\n[Dispense]")
        resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
        print(f"  RX: {resp.hex(' ') if resp else '(none)'}")
    else:
        print("  Skipping dispense — motor rejected")

    time.sleep(1.0)

ser.close()
print("\nDone.")
