#!/usr/bin/env python3
"""Probe the response format by varying each byte position independently.

Send packets with controlled variations to map how the device processes each byte.
"""

import argparse
import time

import serial

HEADER_TX = 0xFE
CMD_HANDSHAKE = 0xA5
CMD_READ_EE = 0xA6


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(b0: int, b1: int, b2: int, b3: int, b4: int) -> bytes:
    pkt = bytes([b0, b1, b2, b3, b4])
    return pkt + bytes([checksum(pkt)])


def send_recv(ser: serial.Serial, pkt: bytes) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    return ser.read(16)


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

    # Handshake first
    pkt = make_pkt(HEADER_TX, CMD_HANDSHAKE, 0, 0, 0)
    resp = send_recv(ser, pkt)
    print(f"Handshake: TX {pkt.hex(' ')} → RX {resp.hex(' ') if resp else '(none)'}")
    time.sleep(1.0)

    # Test 1: Vary byte[2] (address byte) with CMD=ReadEE
    print("\n=== Vary byte[2] with CMD_READ (0xA6) ===")
    for b2 in [0x00, 0x01, 0x02, 0x10, 0x20, 0x40, 0x7F, 0x80, 0x81, 0x90, 0xFE, 0xFF]:
        pkt = make_pkt(HEADER_TX, CMD_READ_EE, b2, 0x00, 0x00)
        resp = send_recv(ser, pkt)
        rx = resp.hex(" ") if resp else "(none)"
        print(f"  b2=0x{b2:02X}: TX {pkt.hex(' ')} → RX {rx}")
        time.sleep(0.1)

    # Test 2: Vary byte[3] with fixed byte[2]=0x82
    print("\n=== Vary byte[3] with b2=0x82 ===")
    for b3 in [0x00, 0x01, 0x02, 0x10, 0x80, 0xFF]:
        pkt = make_pkt(HEADER_TX, CMD_READ_EE, 0x82, b3, 0x00)
        resp = send_recv(ser, pkt)
        rx = resp.hex(" ") if resp else "(none)"
        print(f"  b3=0x{b3:02X}: TX {pkt.hex(' ')} → RX {rx}")
        time.sleep(0.1)

    # Test 3: Vary byte[4] with fixed byte[2]=0x82
    print("\n=== Vary byte[4] with b2=0x82, b3=0x00 ===")
    for b4 in [0x00, 0x01, 0x02, 0x10, 0x80, 0xFF]:
        pkt = make_pkt(HEADER_TX, CMD_READ_EE, 0x82, 0x00, b4)
        resp = send_recv(ser, pkt)
        rx = resp.hex(" ") if resp else "(none)"
        print(f"  b4=0x{b4:02X}: TX {pkt.hex(' ')} → RX {rx}")
        time.sleep(0.1)

    # Test 4: Try wrong checksums to see if checksum is validated
    print("\n=== Wrong checksums ===")
    for bad_cksum in [0x00, 0xFF, 0x01]:
        pkt = bytes([HEADER_TX, CMD_READ_EE, 0x82, 0x00, 0x00, bad_cksum])
        resp = send_recv(ser, pkt)
        rx = resp.hex(" ") if resp else "(none)"
        print(f"  cksum=0x{bad_cksum:02X} (correct=0x28): TX {pkt.hex(' ')} → RX {rx}")
        time.sleep(0.1)

    # Test 5: Try sending 7-byte packets (maybe the real format IS 7 bytes?)
    print("\n=== 7-byte packets ===")
    for extra in [0x00, 0x01, 0x82]:
        base = bytes([HEADER_TX, CMD_READ_EE, 0x00, 0x82, 0x00, 0x00])
        ck = sum(base[1:6]) & 0xFF
        pkt = base + bytes([ck])
        resp = send_recv(ser, pkt)
        rx = resp.hex(" ") if resp else "(none)"
        print(f"  7-byte: TX {pkt.hex(' ')} → RX {rx}")
        time.sleep(0.1)

    # Test 6: Send raw handshake then immediately read to check async response
    print("\n=== Handshake + rapid read ===")
    ser.reset_input_buffer()
    pkt = make_pkt(HEADER_TX, CMD_HANDSHAKE, 0, 0, 0)
    ser.write(pkt)
    ser.flush()
    time.sleep(0.5)
    # Now send ReadEE for 0x82 and read lots of bytes
    pkt = make_pkt(HEADER_TX, CMD_READ_EE, 0x82, 0x00, 0x00)
    ser.write(pkt)
    ser.flush()
    time.sleep(1.5)
    resp = ser.read(64)
    print(f"  All bytes received ({len(resp)}): {resp.hex(' ') if resp else '(none)'}")

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
