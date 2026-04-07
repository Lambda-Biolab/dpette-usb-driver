#!/usr/bin/env python3
"""Deep probe of newly discovered commands: 0xA1, 0xA2 (13-byte responses)
and 0xB0-0xB7 (new range with b2=0x01).

Varies payload bytes to map each command's behavior.
"""

import argparse
import time

import serial

HEADER_TX = 0xFE


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    )

    # Handshake
    resp = send_recv(ser, make_pkt(0xA5))
    print(f"Handshake: {resp.hex(' ') if resp else 'FAILED'}")
    time.sleep(0.5)

    # ===== 0xA1 — 13-byte response =====
    print("\n=== CMD 0xA1 (13-byte response) — vary b2 ===")
    for b2 in [0x00, 0x01, 0x02, 0x10, 0x50, 0x80, 0xFF]:
        pkt = make_pkt(0xA1, b2)
        resp = send_recv(ser, pkt, wait=0.5)
        print(f"  b2=0x{b2:02X}: TX {pkt.hex(' ')}")
        print(f"         RX ({len(resp):2d}b): {resp.hex(' ')}")

    print("\n=== CMD 0xA1 — vary b3 ===")
    for b3 in [0x00, 0x01, 0x10, 0x80, 0xFF]:
        pkt = make_pkt(0xA1, 0x00, b3)
        resp = send_recv(ser, pkt, wait=0.5)
        print(f"  b3=0x{b3:02X}: RX ({len(resp):2d}b): {resp.hex(' ')}")

    print("\n=== CMD 0xA1 — vary b4 ===")
    for b4 in [0x00, 0x01, 0x10, 0x80, 0xFF]:
        pkt = make_pkt(0xA1, 0x00, 0x00, b4)
        resp = send_recv(ser, pkt, wait=0.5)
        print(f"  b4=0x{b4:02X}: RX ({len(resp):2d}b): {resp.hex(' ')}")

    # ===== 0xA2 — 13-byte response =====
    print("\n=== CMD 0xA2 (13-byte response) — vary b2 ===")
    for b2 in [0x00, 0x01, 0x02, 0x10, 0x50, 0x80, 0xFF]:
        pkt = make_pkt(0xA2, b2)
        resp = send_recv(ser, pkt, wait=0.5)
        print(f"  b2=0x{b2:02X}: TX {pkt.hex(' ')}")
        print(f"         RX ({len(resp):2d}b): {resp.hex(' ')}")

    # ===== 0xB0-0xB7 — new range =====
    print("\n=== CMD 0xB0-0xB7 — vary b2 ===")
    for cmd in range(0xB0, 0xB8):
        for b2 in [0x00, 0x01, 0x50, 0xFF]:
            pkt = make_pkt(cmd, b2)
            resp = send_recv(ser, pkt, wait=0.3)
            print(
                f"  cmd=0x{cmd:02X} b2=0x{b2:02X}: RX ({len(resp):2d}b): {resp.hex(' ')}"
            )

    # ===== 0xB0-0xB7 — vary b3 with b2=0x01 =====
    print("\n=== CMD 0xB0 — vary b3 (b2=0x01) ===")
    for b3 in [0x00, 0x01, 0x10, 0x50, 0x80, 0xFF]:
        pkt = make_pkt(0xB0, 0x01, b3)
        resp = send_recv(ser, pkt, wait=0.3)
        print(f"  b3=0x{b3:02X}: RX ({len(resp):2d}b): {resp.hex(' ')}")

    # ===== Send 0xB0 with various b2 values — WATCH FOR MOTOR =====
    print("\n=== CMD 0xB0 with larger b2 values — WATCH PIPETTE ===")
    for b2 in [0x10, 0x20, 0x40, 0x64, 0x80, 0xC8, 0xFF]:
        pkt = make_pkt(0xB0, b2)
        resp = send_recv(ser, pkt, wait=1.0)
        print(f"  b2=0x{b2:02X} ({b2:3d}): RX ({len(resp):2d}b): {resp.hex(' ')}")

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
