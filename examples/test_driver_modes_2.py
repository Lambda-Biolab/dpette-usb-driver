#!/usr/bin/env python3
"""EXP-052b: Test mix, split, and dilution modes.

Continues from where test_driver_modes.py step 3 left off.
Steps 1-3 (PI aspirate/dispense, volume switching, speed control) confirmed working.

Usage:
    python examples/test_driver_modes_2.py [--port /dev/cu.usbserial-0001]
"""

from __future__ import annotations

import argparse
import logging
import sys

from dpette.config import SerialConfig, guess_default_port
from dpette.driver import DPetteDriver
from dpette.protocol import WorkingMode


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-052b: Mix, split, dilution tests")
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("captures/exp052b_modes.log", mode="w"),
        ],
    )
    log = logging.getLogger("EXP-052b")

    port = args.port or guess_default_port()
    if port is None:
        print("ERROR: No serial port found.", file=sys.stderr)
        sys.exit(1)

    cfg = SerialConfig(port=port)
    drv = DPetteDriver(cfg)

    try:
        log.info("=" * 60)
        log.info("EXP-052b: Mix, split, dilution tests")
        log.info("=" * 60)

        drv.connect()
        log.info("Connected (A0 + B0 PI mode).\n")

        # ---- Mixing ----
        log.info("=" * 60)
        log.info("TEST 4: Mix — 100 uL, 3 cycles, speed 3")
        log.info("=" * 60)

        for i in range(1, 4):
            input(f">>> Cycle {i}/3: Put tip IN liquid, press Enter to aspirate...")
            drv.mix_aspirate(100.0, speed=3)
            input(
                f">>> Cycle {i}/3: RAISE tip ABOVE liquid, press Enter to dispense..."
            )
            drv.mix_dispense()
            log.info("Mix cycle %d/3 complete.", i)

        input(">>> Mix done. Tip in air. Press Enter to continue...\n")

        # ---- Splitting ----
        log.info("=" * 60)
        log.info("TEST 5: Split — 100 uL x 3 aliquots")
        log.info("=" * 60)
        log.info("Setting up ST mode (motor homes now)...")
        drv.split_setup(100.0, count=3)

        input(">>> Put tip IN liquid, press Enter to aspirate...")
        drv.split_aspirate()

        input(">>> RAISE tip ABOVE liquid, press Enter to dispense aliquot 1...")
        drv.split_dispense()

        input(">>> Put tip IN liquid, press Enter to dispense aliquot 2...")
        drv.split_dispense()

        input(">>> Put tip IN liquid, press Enter to dispense aliquot 3...")
        drv.split_dispense()

        input(">>> Split done. Press Enter to continue...\n")

        # ---- Dilution ----
        log.info("=" * 60)
        log.info("TEST 6: Dilution — vol1=200 uL (diluent), vol2=100 uL (sample)")
        log.info("=" * 60)
        log.info("Setting up DI mode (motor homes now)...")
        drv.dilute_setup(200.0, 100.0)

        input(">>> Put tip IN diluent, press Enter to aspirate vol1=200 uL...")
        drv.dilute_aspirate()
        log.info("First aspirate done (diluent).")

        input(
            ">>> Move tip to sample, put tip IN liquid, press Enter to aspirate vol2=100 uL..."
        )
        drv.dilute_aspirate()
        log.info("Second aspirate done (sample on top of diluent).")

        input(">>> RAISE tip ABOVE liquid, press Enter to dispense all...")
        log.info("Switching to PI mode to dispense (DI blow doesn't work on dPette)...")
        drv.enter_mode(WorkingMode.PI)
        drv.dispense()
        log.info("Dispense done (vol1 + vol2 together via PI blow).")

        input(">>> Dilution done. Press Enter to continue...\n")

        # ---- Done ----
        log.info("=" * 60)
        log.info("ALL TESTS COMPLETE")
        log.info("=" * 60)

    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        drv.disconnect()


if __name__ == "__main__":
    main()
