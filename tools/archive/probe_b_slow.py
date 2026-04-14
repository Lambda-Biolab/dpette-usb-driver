#!/usr/bin/env python3
"""Send each B-range command one at a time with long pauses.

After each command, waits for you to report what happened.
Press Enter to continue to the next command.
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


def send_recv(ser: serial.Serial, pkt: bytes) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(0.5)
    return ser.read(32)


def main() -> None:
    ser = serial.Serial(
        port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=2.0
    )

    # Handshake
    resp = send_recv(ser, make_pkt(0xA5))
    print(f"Handshake: {resp.hex(' ') if resp else 'FAILED'}")
    time.sleep(1.0)

    probes = [
        ("B0 b2=0x00", 0xB0, 0x00),
        ("B0 b2=0x01 (toggle!)", 0xB0, 0x01),
        ("B1 b2=0x00", 0xB1, 0x00),
        ("B1 b2=0x01", 0xB1, 0x01),
        ("B2 b2=0x00", 0xB2, 0x00),
        ("B2 b2=0x01", 0xB2, 0x01),
        ("B3 b2=0x00", 0xB3, 0x00),
        ("B3 b2=0x01 (toggle!)", 0xB3, 0x01),
        ("B4 b2=0x00", 0xB4, 0x00),
        ("B4 b2=0x01", 0xB4, 0x01),
        ("B5 b2=0x00", 0xB5, 0x00),
        ("B5 b2=0x01", 0xB5, 0x01),
        ("B6 b2=0x00", 0xB6, 0x00),
        ("B6 b2=0x01", 0xB6, 0x01),
        ("B7 b2=0x00", 0xB7, 0x00),
        ("B7 b2=0x01", 0xB7, 0x01),
        # Also test A-range cmds that might have caused sound
        ("A0 b2=0x00", 0xA0, 0x00),
        ("A1 b2=0x00 (13-byte)", 0xA1, 0x00),
        ("A2 b2=0x00 (13-byte)", 0xA2, 0x00),
        ("A3 b2=0x00", 0xA3, 0x00),
        ("A7 b2=0x00", 0xA7, 0x00),
    ]

    for i, (label, cmd, b2) in enumerate(probes):
        pkt = make_pkt(cmd, b2)
        print(f"\n[{i + 1}/{len(probes)}] >>> {label}")
        print(f"    TX: {pkt.hex(' ')}")
        resp = send_recv(ser, pkt)
        print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
        print("    Did the pipette react? (sound/motor/display)")
        sys.stdout.flush()

        # Wait 3 seconds so user can observe
        time.sleep(3.0)

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
