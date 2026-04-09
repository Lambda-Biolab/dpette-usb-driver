#!/usr/bin/env python3
"""Read and display the pipette's EEPROM calibration data.

Reads firmware version, calibration coefficients (k/b), volume
ranges, and factory defaults from the device's EEPROM.

Usage:
    python examples/read_eeprom.py
"""

import time

from dpette.config import SerialConfig, guess_default_port
from dpette.protocol import Command, encode_packet, read_ee_packet
from dpette.serial_link import SerialLink


def main() -> None:
    port = guess_default_port() or "/dev/cu.usbserial-0001"
    cfg = SerialConfig(port=port)
    link = SerialLink(cfg)

    print(f"Connecting to dPette on {port}...")
    link.open()

    # Handshake
    link.write(encode_packet(Command.HELLO))
    time.sleep(1.0)
    resp = link.read(6)
    print(f"Handshake: {resp.hex(' ')}")
    print()

    # Read EEPROM
    def read_byte(addr: int) -> int:
        link.write(read_ee_packet(addr))
        time.sleep(0.2)
        r = link.read(6)
        return r[2] if len(r) >= 3 else 0

    def read_u32(base: int) -> int:
        b = [read_byte(base + i) for i in range(4)]
        return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)

    # Firmware version
    ver = "".join(chr(read_byte(0x60 + i)) for i in range(8))
    print(f"Firmware: {ver.strip(chr(0)).strip(chr(0xFF))}")
    print()

    # Calibration coefficients
    print("Calibration coefficients:")
    for seg, bk, bb in [(1, 0x90, 0x94), (2, 0x98, 0x9C)]:
        k = read_u32(bk)
        b = read_u32(bb)
        print(f"  Segment {seg}: k={k / 10000:.4f}  b={b / 10000:.4f}")

    print()
    print("Factory defaults:")
    for seg, bk, bb in [(1, 0xA0, 0xA4), (2, 0xA8, 0xAC)]:
        k = read_u32(bk)
        b = read_u32(bb)
        print(f"  Segment {seg}: k={k / 10000:.4f}  b={b / 10000:.4f}")

    # Volume range
    print()
    max_vol_lo = read_byte(0xB2)
    max_vol_hi = read_byte(0xB3)
    max_vol = (max_vol_hi << 8) | max_vol_lo
    print(f"Max volume: {max_vol} µL")

    link.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
