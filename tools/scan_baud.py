#!/usr/bin/env python3
"""Scan candidate baud rates and report any that yield a response.

Usage::

    python tools/scan_baud.py [--port /dev/ttyUSB0]

Iterates over DEFAULT_BAUD_CANDIDATES, sends a single null byte as a
probe, and prints whether a response was received.
"""

from __future__ import annotations

import argparse
import sys

from dpette.config import DEFAULT_BAUD_CANDIDATES, SerialConfig, guess_default_port
from dpette.logging_utils import get_logger
from dpette.serial_link import SerialLink

log = get_logger("scan_baud")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan baud rates for dPette response")
    parser.add_argument(
        "--port",
        default=guess_default_port(),
        help="Serial port (default: auto-detect)",
    )
    parser.add_argument(
        "--probe",
        default="00",
        help="Hex string to send as probe (default: '00')",
    )
    args = parser.parse_args()

    if args.port is None:
        log.error("No serial port found — specify --port")
        sys.exit(1)

    probe = bytes.fromhex(args.probe)
    log.info("Probing %s with %s", args.port, probe.hex(" "))

    for baud in DEFAULT_BAUD_CANDIDATES:
        cfg = SerialConfig(port=args.port, baudrate=baud, timeout=0.5)
        try:
            with SerialLink(cfg) as link:
                link.write(probe)
                resp = link.read(64)
                if resp:
                    log.info("[HIT]  %6d baud -> %d bytes: %s", baud, len(resp), resp.hex(" "))
                else:
                    log.info("[MISS] %6d baud -> no response", baud)
        except Exception as exc:
            log.warning("[ERR]  %6d baud -> %s", baud, exc)


if __name__ == "__main__":
    main()
