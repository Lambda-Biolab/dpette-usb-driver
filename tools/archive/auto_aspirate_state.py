#!/usr/bin/env python3
"""Automatic state read before/after aspirate+dispense cycle.

No user input needed — runs the full sequence and logs everything.
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


def send_recv(ser: serial.Serial, pkt: bytes, wait: float = 0.5) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


def read_all_state(ser: serial.Serial, label: str) -> None:
    print(f"\n  --- {label} ---")
    for cmd, name in [
        (0xA0, "A0"),
        (0xA1, "A1"),
        (0xA2, "A2"),
        (0xA3, "A3"),
        (0xA7, "A7"),
    ]:
        resp = send_recv(ser, make_pkt(cmd), wait=0.3)
        print(f"    {name}: ({len(resp):2d}b) {resp.hex(' ')}")
    for cmd in range(0xB0, 0xB8):
        resp = send_recv(ser, make_pkt(cmd, 0x00), wait=0.2)
        print(
            f"    B{cmd - 0xB0}: ({len(resp):2d}b) {resp.hex(' ') if resp else '(none)'}"
        )


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

# Handshake
resp = send_recv(ser, make_pkt(0xA5))
print(f"Handshake: {resp.hex(' ')}")

# 1. Baseline
print("\n" + "=" * 60)
print("STEP 1: BASELINE")
read_all_state(ser, "before anything")

# 2. Aspirate
print("\n" + "=" * 60)
print("STEP 2: ASPIRATE")
pkt = make_pkt(0xB3, 0x01)
print(f"  TX: {pkt.hex(' ')}")
resp = send_recv(ser, pkt, wait=3.0)
print(f"  RX ({len(resp):2d}b): {resp.hex(' ')}")

# 3. State after aspirate
print("\n" + "=" * 60)
print("STEP 3: STATE AFTER ASPIRATE")
read_all_state(ser, "post-aspirate")

# 4. Dispense
print("\n" + "=" * 60)
print("STEP 4: DISPENSE")
pkt = make_pkt(0xB0, 0x01)
print(f"  TX: {pkt.hex(' ')}")
resp = send_recv(ser, pkt, wait=3.0)
print(f"  RX ({len(resp):2d}b): {resp.hex(' ')}")

# 5. State after dispense
print("\n" + "=" * 60)
print("STEP 5: STATE AFTER DISPENSE")
read_all_state(ser, "post-dispense")

# 6. Second aspirate
print("\n" + "=" * 60)
print("STEP 6: SECOND ASPIRATE")
pkt = make_pkt(0xB3, 0x01)
print(f"  TX: {pkt.hex(' ')}")
resp = send_recv(ser, pkt, wait=3.0)
print(f"  RX ({len(resp):2d}b): {resp.hex(' ')}")

# 7. State after second aspirate
print("\n" + "=" * 60)
print("STEP 7: STATE AFTER SECOND ASPIRATE")
read_all_state(ser, "post-aspirate-2")

# 8. Second dispense
print("\n" + "=" * 60)
print("STEP 8: SECOND DISPENSE")
pkt = make_pkt(0xB0, 0x01)
print(f"  TX: {pkt.hex(' ')}")
resp = send_recv(ser, pkt, wait=3.0)
print(f"  RX ({len(resp):2d}b): {resp.hex(' ')}")

# 9. Final state
print("\n" + "=" * 60)
print("STEP 9: FINAL STATE")
read_all_state(ser, "post-dispense-2")

ser.close()
print("\n" + "=" * 60)
print("Done.")
