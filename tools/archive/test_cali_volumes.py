#!/usr/bin/env python3
"""Verify A6 volume control with multiple volumes.

Tests 50, 150, 250 µL — enters cal mode once, sets volume,
exits, aspirates, measures. Repeats for each volume.

Run directly:
    python tools/test_cali_volumes.py
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


def set_volume_via_cal(ser: serial.Serial, vol_ul: int) -> None:
    """Enter cal mode, set volume, exit cal mode."""
    # Enter cal mode
    send_recv(ser, make_pkt(0xA5, 0x01), wait=2.0)
    print("    Entered cal mode (clear Err4 with button if needed)")
    input("    Press ENTER when cal menu is showing: ")

    # Set volume
    resp = send_recv(ser, vol_pkt(vol_ul), wait=0.5)
    print(f"    A6={vol_ul}uL sent. RX: {resp.hex(' ') if resp else '(none)'}")

    # Exit cal mode
    send_recv(ser, make_pkt(0xA5, 0x00), wait=1.0)
    print("    Exited cal mode (clear Err4 with button if needed)")
    input("    Press ENTER when normal menu is back: ")


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

print("=== MULTI-VOLUME VERIFICATION ===")
print("Display should be at 100 µL. We'll test 50, 150, 250.\n")

# Handshake
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"Handshake: {resp.hex(' ')}\n")

for vol in [50, 150, 250]:
    print(f"{'=' * 50}")
    print(f"TEST: Set volume to {vol} µL via cal mode")
    print(f"{'=' * 50}")

    set_volume_via_cal(ser, vol)

    # Re-handshake after cal mode exit
    resp = send_recv(ser, make_pkt(0xA5, 0x00), wait=0.5)
    print(f"    Re-handshake: {resp.hex(' ') if resp else '(none)'}")

    # Aspirate
    print(f"\n    Aspirating (should draw ~{vol} µL)...")
    input("    Press ENTER: ")
    resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
    print(f"    RX: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
    note = input(f"    How much did it draw? (expecting ~{vol}): ")
    print(f"    >> {note}")

    # Dispense
    print("    Dispensing...")
    resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
    print(f"    RX: {resp.hex(' ') if resp else '(none)'}\n")

ser.close()
print("Done.")
