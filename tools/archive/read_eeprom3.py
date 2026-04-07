#!/usr/bin/env python3
"""Read EEPROM v3 — try address as single byte in position [2].

Theory: the device reads addr from byte[2], not bytes[2:3].
When we send [FE A6 00 80 00 xx], the MCU sees addr=0x00.

New format to try:
  [0xFE] [0xA6] [addr] [0x00] [0x00] [checksum]
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


def make_read_ee_v1(addr: int) -> bytes:
    """Address as single byte in position [2]."""
    pkt = bytes([HEADER_TX, CMD_READ_EE, addr & 0xFF, 0x00, 0x00])
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

    # Handshake
    print("[Handshake]")
    resp = send_recv(ser, make_handshake())
    print(f"  RX: {resp.hex(' ') if resp else '(none)'}")
    time.sleep(1.0)

    # Read with address in byte[2]
    print("\n[ReadEE with addr in byte[2]]")
    for addr in [
        0x80,
        0x81,
        0x82,
        0x83,
        0x84,
        0x85,
        0x86,
        0x87,
        0x88,
        0x89,
        0x8A,
        0x8B,
        0x8C,
        0x90,
        0x91,
        0x92,
        0x93,
        0x94,
        0x95,
        0x96,
        0x97,
        0xA0,
        0xA1,
        0xA2,
        0xA3,
        0xA4,
        0xA5,
        0xA6,
        0xA7,
    ]:
        time.sleep(0.15)
        pkt = make_read_ee_v1(addr)
        resp = send_recv(ser, pkt)
        if resp:
            print(
                f"  0x{addr:02X}: TX {pkt.hex(' ')}  RX ({len(resp):2d}b): {resp.hex(' ')}"
            )
        else:
            print(f"  0x{addr:02X}: (timeout)")

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
