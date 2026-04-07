#!/usr/bin/env python3
"""Test if CMD=0xA4 with value=0 acts as a read command.

WriteEE: [FE] [A4] [addr_hi] [addr_lo] [value] [checksum]

We'll also try single-byte address format and listen for async responses.
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


def send_recv(
    ser: serial.Serial, pkt: bytes, read_bytes: int = 32, wait: float = 1.0
) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(read_bytes)


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

    # HandShake
    resp = send_recv(ser, make_pkt(0xA5), wait=0.5)
    print(f"Handshake: {resp.hex(' ') if resp else '(none)'}")

    # Test CMD=0xA4 with 2-byte address (big-endian) and value=0
    print("\n=== CMD=0xA4 [addr_hi][addr_lo] val=0 ===")
    for addr in [0x0082, 0x0090, 0x00A0]:
        hi = (addr >> 8) & 0xFF
        lo = addr & 0xFF
        pkt = make_pkt(0xA4, hi, lo, 0x00)
        resp = send_recv(ser, pkt, wait=1.0)
        print(
            f"  addr=0x{addr:04X}: TX {pkt.hex(' ')} → RX ({len(resp)}b): {resp.hex(' ') if resp else '(none)'}"
        )

    # Test CMD=0xA4 single-byte address, value=0
    print("\n=== CMD=0xA4 [addr] [0] [0] ===")
    for addr in [0x82, 0x83, 0x90, 0x91, 0xA0]:
        pkt = make_pkt(0xA4, addr, 0x00, 0x00)
        resp = send_recv(ser, pkt, wait=1.0)
        print(
            f"  addr=0x{addr:02X}: TX {pkt.hex(' ')} → RX ({len(resp)}b): {resp.hex(' ') if resp else '(none)'}"
        )

    # Test: all 4 CMDs with addr=0x82
    print("\n=== All CMDs with b2=0x82 ===")
    for cmd, name in [
        (0xA3, "A3"),
        (0xA4, "A4"),
        (0xA5, "A5"),
        (0xA6, "A6"),
        (0xA7, "A7"),
        (0xA8, "A8"),
        (0xA0, "A0"),
        (0xAF, "AF"),
        (0x01, "01"),
        (0x06, "06"),
        (0x03, "03"),
    ]:
        pkt = make_pkt(cmd, 0x82, 0x00, 0x00)
        resp = send_recv(ser, pkt, wait=0.5)
        rx = resp.hex(" ") if resp else "(none)"
        print(f"  CMD=0x{cmd:02X}: TX {pkt.hex(' ')} → RX: {rx}")

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
