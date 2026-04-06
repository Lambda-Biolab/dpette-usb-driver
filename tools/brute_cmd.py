#!/usr/bin/env python3
"""Brute-force all 256 CMD bytes after handshake.

Sends [FE] [CMD] [00] [00] [00] [cksum] for CMD 0x00-0xFF.
Logs which CMDs get a response and what the response is.

WATCH THE PIPETTE for physical reactions (motor, display, sounds).

Usage:
    python tools/brute_cmd.py --port /dev/cu.usbserial-0001
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout", type=float, default=0.5)
    parser.add_argument(
        "--pause",
        type=float,
        default=0.3,
        help="seconds between probes (watch the pipette!)",
    )
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
    ser.reset_input_buffer()
    ser.write(make_pkt(0xA5))
    ser.flush()
    resp = ser.read(6)
    print(f"Handshake: {resp.hex(' ') if resp else 'FAILED'}")
    if not resp:
        print("Handshake failed — is the pipette awake?")
        ser.close()
        return
    time.sleep(1.0)

    print(f"\nScanning CMD 0x00-0xFF (pause={args.pause}s per probe)")
    print(">>> WATCH THE PIPETTE for motor/display/sound <<<")
    print("-" * 70)

    hits = []
    silent = []

    for cmd in range(256):
        pkt = make_pkt(cmd)
        ser.reset_input_buffer()
        ser.write(pkt)
        ser.flush()

        # Read up to 32 bytes in case of multi-packet response
        time.sleep(args.pause)
        resp = ser.read(32)

        if resp:
            hex_rx = resp.hex(" ")
            print(
                f"  0x{cmd:02X} ✓  TX: {pkt.hex(' ')}  RX ({len(resp):2d}b): {hex_rx}"
            )
            hits.append((cmd, resp))
        else:
            silent.append(cmd)

        # Re-handshake every 32 cmds to keep connection alive
        if (cmd + 1) % 32 == 0 and cmd < 255:
            ser.reset_input_buffer()
            ser.write(make_pkt(0xA5))
            ser.flush()
            hs = ser.read(6)
            if not hs:
                print(f"  *** Re-handshake failed at CMD 0x{cmd:02X} ***")
            time.sleep(0.3)

    # Summary
    print("\n" + "=" * 70)
    print(f"RESPONDING CMDs ({len(hits)}):")
    for cmd, resp in hits:
        # Parse response cmd byte
        resp_cmd = resp[1] if len(resp) > 1 else 0
        same = "=" if resp_cmd == cmd else f"→0x{resp_cmd:02X}"
        print(f"  0x{cmd:02X} {same}  RX: {resp.hex(' ')}")

    print(f"\nSILENT CMDs ({len(silent)}): ", end="")
    # Compact range display
    if silent:
        ranges = []
        start = silent[0]
        end = silent[0]
        for s in silent[1:]:
            if s == end + 1:
                end = s
            else:
                ranges.append(
                    f"0x{start:02X}-0x{end:02X}" if start != end else f"0x{start:02X}"
                )
                start = s
                end = s
        ranges.append(
            f"0x{start:02X}-0x{end:02X}" if start != end else f"0x{start:02X}"
        )
        print(", ".join(ranges))

    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
