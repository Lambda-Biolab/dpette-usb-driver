#!/usr/bin/env python3
"""Try CMD=0xA3 for reading EEPROM — the data handler checks for 0xA3 in responses.

Also try reading more bytes in case the device sends multi-packet responses.
"""

import argparse
import time

import serial

HEADER_TX = 0xFE
CMD_HANDSHAKE = 0xA5
CMD_A3 = 0xA3
CMD_A4 = 0xA4
CMD_A6 = 0xA6


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, cmd, b2, b3, b4])
    return pkt + bytes([checksum(pkt)])


def send_recv(
    ser: serial.Serial, pkt: bytes, read_size: int = 32, wait: float = 0.5
) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(read_size)


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
    resp = send_recv(ser, make_pkt(CMD_HANDSHAKE))
    print(f"Handshake: {resp.hex(' ') if resp else '(none)'}")
    time.sleep(0.5)

    # Test CMD=0xA3 with various addresses
    print("\n=== CMD=0xA3 (possible ReadEE) ===")
    for addr in [0x00, 0x80, 0x82, 0x90, 0xFF]:
        pkt = make_pkt(CMD_A3, addr)
        resp = send_recv(ser, pkt, read_size=64, wait=1.0)
        print(f"  addr=0x{addr:02X}: TX {pkt.hex(' ')}")
        if resp:
            print(f"           RX ({len(resp):2d}b): {resp.hex(' ')}")
        else:
            print("           RX: (none)")

    # Re-handshake
    resp = send_recv(ser, make_pkt(CMD_HANDSHAKE))
    print(f"\nRe-handshake: {resp.hex(' ') if resp else '(none)'}")
    time.sleep(0.5)

    # Test CMD=0xA6 then wait and read a LOT — maybe data comes later
    print("\n=== CMD=0xA6, addr=0x82, read 64 bytes with 2s wait ===")
    pkt = make_pkt(CMD_A6, 0x82)
    resp = send_recv(ser, pkt, read_size=64, wait=2.0)
    print(f"  TX: {pkt.hex(' ')}")
    if resp:
        print(f"  RX ({len(resp):2d}b): {resp.hex(' ')}")
    else:
        print("  RX: (none)")

    # Test: send ReadEE, read ACK, then immediately read more
    print("\n=== CMD=0xA6 double-read ===")
    ser.reset_input_buffer()
    pkt = make_pkt(CMD_A6, 0x82)
    ser.write(pkt)
    ser.flush()
    resp1 = ser.read(6)
    print(f"  TX: {pkt.hex(' ')}")
    print(f"  RX1 ({len(resp1)}b): {resp1.hex(' ') if resp1 else '(none)'}")
    time.sleep(1.0)
    resp2 = ser.read(64)
    print(f"  RX2 ({len(resp2)}b): {resp2.hex(' ') if resp2 else '(none)'}")

    # Try: what about sending multiple reads quickly then reading all responses?
    print("\n=== Rapid-fire 3 reads, then read all ===")
    ser.reset_input_buffer()
    for addr in [0x82, 0x83, 0x90]:
        pkt = make_pkt(CMD_A6, addr)
        ser.write(pkt)
        ser.flush()
        time.sleep(0.05)
    time.sleep(2.0)
    resp = ser.read(128)
    print(f"  RX ({len(resp)}b): {resp.hex(' ') if resp else '(none)'}")

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
