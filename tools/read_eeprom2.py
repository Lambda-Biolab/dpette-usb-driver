#!/usr/bin/env python3
"""Read EEPROM v2 — with post-handshake delay and retry logic.

Also probes response format more carefully.
"""

import argparse
import time

import serial

HEADER_TX = 0xFE
CMD_HANDSHAKE = 0xA5
CMD_READ_EE = 0xA6


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_handshake() -> bytes:
    pkt = bytes([HEADER_TX, CMD_HANDSHAKE, 0x00, 0x00, 0x00])
    return pkt + bytes([checksum(pkt)])


def make_read_ee(addr: int) -> bytes:
    addr_hi = (addr >> 8) & 0xFF
    addr_lo = addr & 0xFF
    pkt = bytes([HEADER_TX, CMD_READ_EE, addr_hi, addr_lo, 0x00])
    return pkt + bytes([checksum(pkt)])


def send_recv(ser: serial.Serial, pkt: bytes, read_size: int = 16) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    return ser.read(read_size)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout", type=float, default=1.5)
    args = parser.parse_args()

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    )

    # Step 1: Handshake
    print("[Handshake]")
    resp = send_recv(ser, make_handshake())
    print(f"  RX: {resp.hex(' ') if resp else '(none)'}")
    print("  Waiting 1s after handshake...")
    time.sleep(1.0)

    # Step 2: Read addresses with generous timeout, reading up to 16 bytes
    # to check if the device sends more than 6 bytes
    print("\n[Read EEPROM — checking response size and format]")

    test_addrs = [
        0x80,
        0x81,
        0x82,
        0x83,
        0x84,
        0x85,
        0x86,
        0x87,
        0x88,
        0x90,
        0x94,
        0xA0,
    ]

    for addr in test_addrs:
        time.sleep(0.15)
        resp = send_recv(ser, make_read_ee(addr), read_size=16)
        if resp:
            print(f"  0x{addr:02X}: RX ({len(resp):2d} bytes): {resp.hex(' ')}")
        else:
            print(f"  0x{addr:02X}: (timeout)")

    # Step 3: Try double-read pattern (handshake again + immediate read)
    print("\n[Re-handshake + immediate read of 0x80]")
    resp = send_recv(ser, make_handshake())
    print(f"  Handshake RX: {resp.hex(' ') if resp else '(none)'}")
    time.sleep(0.5)

    for addr in [0x80, 0x81, 0x82, 0x83]:
        time.sleep(0.15)
        resp = send_recv(ser, make_read_ee(addr), read_size=16)
        if resp:
            print(f"  0x{addr:02X}: RX ({len(resp):2d} bytes): {resp.hex(' ')}")
        else:
            print(f"  0x{addr:02X}: (timeout)")

    # Step 4: Try reading some unusual addresses
    print("\n[Probing other addresses]")
    for addr in [0x00, 0x01, 0x10, 0x20, 0x40, 0x60, 0x7F, 0xB0, 0xC0, 0xFF]:
        time.sleep(0.15)
        resp = send_recv(ser, make_read_ee(addr), read_size=16)
        if resp:
            print(f"  0x{addr:02X}: RX ({len(resp):2d} bytes): {resp.hex(' ')}")
        else:
            print(f"  0x{addr:02X}: (timeout)")

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
