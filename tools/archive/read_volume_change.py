#!/usr/bin/env python3
"""Read all state, user changes volume, read again. Diff the results.

Run directly:
    python tools/read_volume_change.py
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


def send_recv(ser: serial.Serial, pkt: bytes, wait: float = 0.3) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


def read_all(ser: serial.Serial) -> dict[str, bytes]:
    results = {}
    for cmd, name in [
        (0xA0, "A0"),
        (0xA1, "A1"),
        (0xA2, "A2"),
        (0xA3, "A3"),
        (0xA7, "A7"),
    ]:
        results[name] = send_recv(ser, make_pkt(cmd))
    for cmd in range(0xB0, 0xB8):
        results[f"B{cmd - 0xB0}"] = send_recv(ser, make_pkt(cmd, 0x00))
    return results


def print_state(results: dict[str, bytes]) -> None:
    for name, resp in results.items():
        print(f"    {name}: ({len(resp):2d}b) {resp.hex(' ')}")


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

resp = send_recv(ser, make_pkt(0xA5))
print(f"Handshake: {resp.hex(' ')}\n")

print("Reading state at CURRENT volume...")
before = read_all(ser)
print_state(before)

input("\n>>> NOW CHANGE THE VOLUME ON THE PIPETTE, then press ENTER <<<\n")

print("Reading state at NEW volume...")
after = read_all(ser)
print_state(after)

# Diff
print("\n" + "=" * 60)
print("DIFFERENCES:")
any_diff = False
for name in before:
    if before[name] != after[name]:
        any_diff = True
        print(f"  {name} CHANGED:")
        print(f"    before: {before[name].hex(' ')}")
        print(f"    after:  {after[name].hex(' ')}")

if not any_diff:
    print("  (none — all responses identical)")

ser.close()
print("\nDone.")
