#!/usr/bin/env python3
"""Sweep all 256 addresses and log the response byte[2] value.

This maps the device's EEPROM contents across the full address space.
"""

import argparse
import time

import serial

HEADER_TX = 0xFE
CMD_HANDSHAKE = 0xA5
CMD_READ_EE = 0xA6


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(b1: int, b2: int, b3: int = 0, b4: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, b1, b2, b3, b4])
    return pkt + bytes([checksum(pkt)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout", type=float, default=1.0)
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
    pkt = make_pkt(CMD_HANDSHAKE, 0)
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    resp = ser.read(6)
    print(f"Handshake: {resp.hex(' ') if resp else '(none)'}")
    time.sleep(1.0)

    # Sweep all 256 addresses
    print("\nAddr → RX[2] RX[3] RX[4]  (full response)")
    print("-" * 60)

    results = {}
    for addr in range(256):
        pkt = make_pkt(CMD_READ_EE, addr)
        ser.reset_input_buffer()
        ser.write(pkt)
        ser.flush()
        resp = ser.read(6)

        if resp and len(resp) == 6:
            val = (resp[2], resp[3], resp[4])
            results[addr] = val
            # Only print when value changes from previous
            if addr == 0 or val != results.get(addr - 1):
                print(
                    f"  0x{addr:02X}: {resp[2]:02X} {resp[3]:02X} {resp[4]:02X}  ({resp.hex(' ')})"
                )
        else:
            results[addr] = None
            print(f"  0x{addr:02X}: (timeout)")

        time.sleep(0.05)

    # Summary
    print("\n" + "=" * 60)
    print("Summary — unique response values:")
    by_value: dict[tuple[int, int, int], list[int]] = {}
    for addr, val in sorted(results.items()):
        if val is not None:
            by_value.setdefault(val, []).append(addr)

    for val, addrs in sorted(by_value.items()):
        ranges = []
        start = addrs[0]
        end = addrs[0]
        for a in addrs[1:]:
            if a == end + 1:
                end = a
            else:
                ranges.append((start, end))
                start = a
                end = a
        ranges.append((start, end))

        range_strs = []
        for s, e in ranges:
            if s == e:
                range_strs.append(f"0x{s:02X}")
            else:
                range_strs.append(f"0x{s:02X}-0x{e:02X}")

        print(f"  ({val[0]:02X},{val[1]:02X},{val[2]:02X}): {', '.join(range_strs)}")

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
