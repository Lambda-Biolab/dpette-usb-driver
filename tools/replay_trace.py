#!/usr/bin/env python3
"""Replay a saved binary trace file over the serial link.

Usage::

    python tools/replay_trace.py --port /dev/ttyUSB0 --baud 9600 captures/trace.bin

The trace file should contain the raw bytes that were originally sent
to the device (TX side only).  Each byte is replayed faithfully.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from dpette.config import SerialConfig, guess_default_port
from dpette.logging_utils import get_logger
from dpette.serial_link import SerialLink

log = get_logger("replay_trace")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a binary trace to the pipette")
    parser.add_argument("trace", type=Path, help="Path to binary trace file")
    parser.add_argument("--port", default=guess_default_port(), help="Serial port")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds between each byte (default: 0 = full speed)",
    )
    parser.add_argument(
        "--listen",
        type=float,
        default=0.5,
        help="Seconds to listen for a response after sending (default: 0.5)",
    )
    args = parser.parse_args()

    if args.port is None:
        log.error("No serial port found — specify --port")
        sys.exit(1)

    if not args.trace.is_file():
        log.error("Trace file not found: %s", args.trace)
        sys.exit(1)

    payload = args.trace.read_bytes()
    log.info("Loaded %d bytes from %s", len(payload), args.trace)

    cfg = SerialConfig(port=args.port, baudrate=args.baud, timeout=args.listen)

    with SerialLink(cfg) as link:
        log.info("Replaying %d bytes to %s @ %d baud", len(payload), args.port, args.baud)
        link.write(payload)

        if args.delay > 0:
            time.sleep(args.delay)

        # Listen for response
        resp = link.read(4096)
        if resp:
            log.info("Response (%d bytes): %s", len(resp), resp.hex(" "))
        else:
            log.info("No response within %.1fs", args.listen)


if __name__ == "__main__":
    main()
