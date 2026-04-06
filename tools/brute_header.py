#!/usr/bin/env python3
"""Brute-force the header byte by sending all 256 handshake variants.

Handshake packet format (from decompilation):
    [HEADER] [0x00] [0x00] [0x00] [0x00] [0x00] [0x00]

For each possible header byte (0x00–0xFF), send the packet and check
for any response within a short timeout.

Usage:
    python tools/brute_header.py --port /dev/cu.usbserial-0001
"""

import argparse
import time

import serial


def main() -> None:
    parser = argparse.ArgumentParser(description="Brute-force dPette header byte")
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument(
        "--timeout", type=float, default=0.3, help="read timeout per probe"
    )
    args = parser.parse_args()

    print(f"Opening {args.port} @ {args.baud} baud")
    print("Sending 256 handshake variants (header 0x00–0xFF)...")
    print("Make sure the pipette is awake (press the button first)!")
    print("-" * 60)

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    )

    # Flush any stale data
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    hits = []

    try:
        for header in range(256):
            pkt = bytes([header, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

            ser.reset_input_buffer()
            ser.write(pkt)
            ser.flush()

            resp = ser.read(64)

            if resp:
                hex_tx = pkt.hex(" ")
                hex_rx = resp.hex(" ")
                ascii_rx = "".join(chr(b) if 32 <= b < 127 else "." for b in resp)
                print(f"  HIT  header=0x{header:02X}  TX: {hex_tx}")
                print(f"       RX ({len(resp):2d} bytes): {hex_rx}")
                print(f"       ASCII: {ascii_rx}")
                hits.append((header, pkt, resp))

            # Brief pause between probes to avoid flooding
            time.sleep(0.05)

            # Progress every 32 bytes
            if (header + 1) % 32 == 0:
                print(f"  ... tested 0x00–0x{header:02X} ({header + 1}/256)")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        ser.close()

    print("-" * 60)
    if hits:
        print(f"Found {len(hits)} header(s) that got a response:")
        for header, pkt, resp in hits:
            print(f"  0x{header:02X} → {resp.hex(' ')}")
    else:
        print("No responses received for any header byte.")
        print("Possible causes:")
        print("  - Pipette is in standby (press the button to wake it)")
        print("  - Handshake format is wrong (cmd bytes may not be 0x00)")
        print("  - Longer timeout needed (try --timeout 1.0)")


if __name__ == "__main__":
    main()
