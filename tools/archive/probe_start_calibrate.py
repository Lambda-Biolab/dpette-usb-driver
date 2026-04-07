#!/usr/bin/env python3
"""Send StartCalibrate (HandShake with param=1) and listen for async data.

The theory: [FE A5 01 00 00 A6] triggers the device to dump EEPROM
data as 0xA3 response packets.
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


def drain_all(ser: serial.Serial, duration: float = 5.0) -> bytes:
    """Read everything for `duration` seconds."""
    total = b""
    start = time.time()
    while time.time() - start < duration:
        chunk = ser.read(256)
        if chunk:
            total += chunk
    return total


def print_packets(data: bytes) -> None:
    """Print data as 6-byte packets."""
    for i in range(0, len(data), 6):
        pkt = data[i : i + 6]
        hex_str = pkt.hex(" ")
        print(f"    [{i // 6:2d}] ({len(pkt)}b): {hex_str}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout", type=float, default=0.5)
    args = parser.parse_args()

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    )

    # Test 1: HandShake param=0, listen for 3s
    print("=== HandShake param=0 (normal) + 3s listen ===")
    ser.reset_input_buffer()
    pkt = make_pkt(0xA5, 0)
    print(f"TX: {pkt.hex(' ')}")
    ser.write(pkt)
    ser.flush()
    resp = drain_all(ser, 3.0)
    print(f"RX total ({len(resp)}b):")
    if resp:
        print_packets(resp)

    # Test 2: HandShake param=1 (StartCalibrate), listen for 5s
    print("\n=== HandShake param=1 (StartCalibrate) + 5s listen ===")
    ser.reset_input_buffer()
    pkt = make_pkt(0xA5, 1)
    print(f"TX: {pkt.hex(' ')}")
    ser.write(pkt)
    ser.flush()
    resp = drain_all(ser, 5.0)
    print(f"RX total ({len(resp)}b):")
    if resp:
        print_packets(resp)

    # Test 3: HandShake param=0, then param=1, listen
    print("\n=== HS(0) then HS(1) + 5s listen ===")
    ser.reset_input_buffer()
    pkt0 = make_pkt(0xA5, 0)
    ser.write(pkt0)
    ser.flush()
    time.sleep(1.0)
    ser.read(6)  # consume ACK

    pkt1 = make_pkt(0xA5, 1)
    print(f"TX: {pkt1.hex(' ')}")
    ser.write(pkt1)
    ser.flush()
    resp = drain_all(ser, 5.0)
    print(f"RX total ({len(resp)}b):")
    if resp:
        print_packets(resp)

    # Test 4: Try other param values (2-5)
    for p in [2, 3, 4, 5]:
        print(f"\n=== HandShake param={p} + 3s listen ===")
        ser.reset_input_buffer()
        pkt = make_pkt(0xA5, p)
        print(f"TX: {pkt.hex(' ')}")
        ser.write(pkt)
        ser.flush()
        resp = drain_all(ser, 3.0)
        print(f"RX total ({len(resp)}b):")
        if resp:
            print_packets(resp)

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
