#!/usr/bin/env python3
"""Test the real calibration flow: HandShake → CaliVolume → read responses.

Corrected understanding:
  0xA4 = WriteEE (write k/b to EEPROM)
  0xA5 = HandShake
  0xA6 = SendCaliVolume (tells device which volume to calibrate at)
  0xA3 = device response containing EEPROM/calibration data

CaliVolume packet encodes volume×10 as big-endian in bytes[2:3]:
  [FE] [A6] [vol_hi] [vol_lo] [00] [checksum]

Example: 1000 µL → 10000 = 0x2710 → [FE A6 27 10 00 cksum]
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


def make_cali_volume(volume_ul: int) -> bytes:
    """Build a SendCaliVolume packet for volume in µL."""
    val = volume_ul * 10
    hi = (val >> 8) & 0xFF
    lo = val & 0xFF
    return make_pkt(0xA6, hi, lo)


def send_and_drain(
    ser: serial.Serial, pkt: bytes, label: str, wait: float = 1.0
) -> None:
    ser.reset_input_buffer()
    print(f"\n>>> {label}")
    print(f"    TX ({len(pkt)}b): {pkt.hex(' ')}")
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    total = b""
    while True:
        chunk = ser.read(64)
        if not chunk:
            break
        total += chunk
    if total:
        # Parse into 6-byte packets
        for i in range(0, len(total), 6):
            pkt_rx = total[i : i + 6]
            hex_rx = pkt_rx.hex(" ")
            print(f"    RX[{i // 6}] ({len(pkt_rx)}b): {hex_rx}")
    else:
        print("    RX: (none)")


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

    # Step 1: HandShake
    send_and_drain(ser, make_pkt(0xA5), "HandShake")

    # Step 2: Send CaliVolume for various standard volumes
    # dPette 100-1000 µL range calibration points: 100, 500, 1000
    for vol in [100, 500, 1000]:
        send_and_drain(ser, make_cali_volume(vol), f"CaliVolume {vol} µL", wait=2.0)

    # Step 3: Try other volumes
    for vol in [10, 50, 200]:
        send_and_drain(ser, make_cali_volume(vol), f"CaliVolume {vol} µL", wait=2.0)

    # Step 4: Re-handshake then immediately send cali volume
    send_and_drain(ser, make_pkt(0xA5), "Re-HandShake")
    time.sleep(0.5)
    send_and_drain(
        ser, make_cali_volume(1000), "CaliVolume 1000 µL (after fresh HS)", wait=3.0
    )

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
