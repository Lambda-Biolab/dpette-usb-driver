#!/usr/bin/env python3
"""EXP-053: Dilution mode test.

DI mode: aspirate vol1 (diluent), aspirate vol2 (sample), switch to PI, dispense all.
DI blow doesn't trigger the motor on the basic dPette, so we use PI mode for the dispense.

Usage:
    python examples/test_dilution.py [--port /dev/cu.usbserial-0001]
"""

from __future__ import annotations

import argparse
import logging
import sys

from dpette.config import SerialConfig, guess_default_port
from dpette.driver import DPetteDriver
from dpette.protocol import WorkingMode


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-053: Dilution mode test")
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("captures/exp053_dilution.log", mode="w"),
        ],
    )
    log = logging.getLogger("EXP-053")

    port = args.port or guess_default_port()
    if port is None:
        print("ERROR: No serial port found.", file=sys.stderr)
        sys.exit(1)

    cfg = SerialConfig(port=port)
    drv = DPetteDriver(cfg)

    try:
        log.info("=" * 60)
        log.info("EXP-053: Dilution — vol1=200 uL, vol2=100 uL")
        log.info("=" * 60)

        drv.connect()
        log.info("Connected.\n")

        log.info("Setting up DI mode (motor homes now)...")
        drv.dilute_setup(200.0, 100.0)

        input(">>> Put tip IN diluent, press Enter to aspirate vol1=200 uL...")
        drv.dilute_aspirate()
        log.info("First aspirate done (diluent).")

        input(
            ">>> Move tip to sample, put tip IN liquid, press Enter to aspirate vol2=100 uL..."
        )
        drv.dilute_aspirate()
        log.info("Second aspirate done (sample on top).")

        input(">>> RAISE tip ABOVE liquid, press Enter to dispense all...")
        log.info("Entering PI mode — motor homes and expels liquid...")
        drv.enter_mode(WorkingMode.PI)
        log.info("Dispense done.")

        input(">>> Done. Press Enter to finish...")

    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        drv.disconnect()


if __name__ == "__main__":
    main()
