#!/usr/bin/env python3
"""Passive listener — open the serial port and log everything received.

Usage:
    python tools/passive_listen.py --port /dev/cu.usbserial-0001

Press the pipette's operation button while this is running to see if
the MCU sends anything unprompted.
"""

import argparse
import time

import serial


def main() -> None:
    parser = argparse.ArgumentParser(description="Passive serial listener for dPette")
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--duration", type=int, default=30, help="seconds to listen")
    args = parser.parse_args()

    print(f"Opening {args.port} @ {args.baud} baud")
    print(f"Listening for {args.duration}s — press the pipette button now!")
    print("-" * 60)

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=0.5,
    )

    start = time.time()
    total_bytes = 0

    try:
        while time.time() - start < args.duration:
            data = ser.read(256)
            if data:
                elapsed = time.time() - start
                total_bytes += len(data)
                hex_str = data.hex(" ")
                ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
                print(f"[{elapsed:6.1f}s] ({len(data):3d} bytes) {hex_str}")
                print(f"         ASCII: {ascii_str}")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        ser.close()

    print("-" * 60)
    print(f"Done. Received {total_bytes} bytes total in {args.duration}s.")


if __name__ == "__main__":
    main()
