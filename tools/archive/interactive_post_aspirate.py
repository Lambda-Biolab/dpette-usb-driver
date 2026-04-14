#!/usr/bin/env python3
"""Read A1/A2 data before and after aspirate to detect state changes.

Also reads A1/A2 after dispense to see if values reset.

Run directly:
    python tools/interactive_post_aspirate.py
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


def send_recv(ser: serial.Serial, pkt: bytes, wait: float = 1.0) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

# Handshake
resp = send_recv(ser, make_pkt(0xA5))
print(f"Handshake: {resp.hex(' ')}\n")


def read_state(label: str) -> None:
    """Read A1, A2, and all B-range status."""
    print(f"  [{label}]")
    for cmd, name in [(0xA1, "A1"), (0xA2, "A2")]:
        resp = send_recv(ser, make_pkt(cmd), wait=0.5)
        print(f"    {name}: ({len(resp):2d}b) {resp.hex(' ')}")
    for cmd in range(0xB0, 0xB8):
        resp = send_recv(ser, make_pkt(cmd, 0x00), wait=0.3)
        b2_val = resp[2] if len(resp) > 2 else -1
        print(
            f"    B{cmd - 0xB0} status: b2=0x{b2_val:02X}"
            if b2_val >= 0
            else f"    B{cmd - 0xB0}: (none)"
        )
    print()


steps = [
    ("BASELINE — before anything", None),
    ("ASPIRATE — watch the pipette", "aspirate"),
    ("AFTER ASPIRATE — reading state", None),
    ("DISPENSE — watch the pipette", "dispense"),
    ("AFTER DISPENSE — reading state", None),
    ("SECOND ASPIRATE", "aspirate"),
    ("AFTER SECOND ASPIRATE", None),
    ("SECOND DISPENSE", "dispense"),
    ("AFTER SECOND DISPENSE", None),
]

for i, (label, action) in enumerate(steps):
    print(f"=== Step {i + 1}/{len(steps)}: {label} ===")

    if action == "aspirate":
        input("Press ENTER to aspirate: ")
        pkt = make_pkt(0xB3, 0x01)
        print(f"  TX: {pkt.hex(' ')}")
        resp = send_recv(ser, pkt, wait=2.0)
        print(f"  RX ({len(resp):2d}b): {resp.hex(' ')}")
        note = input("  What happened? ")
        print(f"  >> {note}\n")
    elif action == "dispense":
        input("Press ENTER to dispense: ")
        pkt = make_pkt(0xB0, 0x01)
        print(f"  TX: {pkt.hex(' ')}")
        resp = send_recv(ser, pkt, wait=2.0)
        print(f"  RX ({len(resp):2d}b): {resp.hex(' ')}")
        note = input("  What happened? ")
        print(f"  >> {note}\n")
    else:
        read_state(label)
        input("Press ENTER to continue: ")
        print()

ser.close()
print("Done.")
