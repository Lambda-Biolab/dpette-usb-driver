#!/usr/bin/env python3
"""Dump raw hex from a serial port until Ctrl-C.

Usage::

    python tools/dump_raw.py --port /dev/ttyUSB0 --baud 9600
"""

from __future__ import annotations

import argparse
import sys
import time

from dpette.config import SerialConfig, guess_default_port
from dpette.logging_utils import get_logger
from dpette.serial_link import SerialLink

log = get_logger("dump_raw")

CHUNK = 256


def main() -> None:
    parser = argparse.ArgumentParser(description="Hex-dump raw serial traffic")
    parser.add_argument("--port", default=guess_default_port(), help="Serial port")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    args = parser.parse_args()

    if args.port is None:
        log.error("No serial port found — specify --port")
        sys.exit(1)

    cfg = SerialConfig(port=args.port, baudrate=args.baud, timeout=0.1)
    log.info("Listening on %s @ %d baud — press Ctrl-C to stop", args.port, args.baud)

    try:
        with SerialLink(cfg) as link:
            offset = 0
            while True:
                data = link.read(CHUNK)
                if data:
                    hex_str = data.hex(" ")
                    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
                    print(f"{offset:08x}  {hex_str:<{CHUNK * 3}}  |{ascii_str}|")
                    offset += len(data)
    except KeyboardInterrupt:
        print(f"\nStopped. {offset} bytes captured.")


if __name__ == "__main__":
    main()
