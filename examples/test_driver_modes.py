#!/usr/bin/env python3
"""EXP-052: Test the new driver API — PI, ST, DI modes + mixing.

Exercises every high-level method with full TX/RX logging so we can
verify the protocol bytes match the official DLAB spec.

Usage:
    python examples/test_driver_modes.py [--port /dev/cu.usbserial-0001]
"""

from __future__ import annotations

import argparse
import logging
import sys

from dpette.config import SerialConfig, guess_default_port
from dpette.driver import DPetteDriver
from dpette.protocol import KeyAction


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-052: Driver mode tests")
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("captures/exp052_driver_modes.log", mode="w"),
        ],
    )
    log = logging.getLogger("EXP-052")

    port = args.port or guess_default_port()
    if port is None:
        print("ERROR: No serial port found.", file=sys.stderr)
        sys.exit(1)

    cfg = SerialConfig(port=port)
    drv = DPetteDriver(cfg)

    try:
        # ---- Connect ----
        log.info("=" * 60)
        log.info("EXP-052: Full driver mode test")
        log.info("=" * 60)

        drv.connect()
        log.info("Connected.\n")

        # ---- PI mode: aspirate + dispense ----
        log.info("=" * 60)
        log.info("TEST 1: PI mode — aspirate 150 uL, dispense")
        log.info("=" * 60)
        input(">>> Tip in water, ready? Press Enter...")

        pkt = drv.aspirate(150.0)
        log.info("Aspirate result: cmd=%02x b2=%02x", pkt.cmd, pkt.b2)

        input(">>> Press Enter to dispense...")

        pkt = drv.dispense()
        log.info("Dispense result: cmd=%02x b2=%02x", pkt.cmd, pkt.b2)

        # ---- PI mode: change volume on the fly ----
        log.info("")
        log.info("=" * 60)
        log.info("TEST 2: PI mode — aspirate 50 uL, then 250 uL")
        log.info("=" * 60)
        input(">>> Press Enter to aspirate 50 uL...")

        drv.aspirate(50.0)
        log.info("Aspirated 50 uL.")

        input(">>> Observe small amount. Press Enter to dispense...")
        drv.dispense()

        input(">>> Press Enter to aspirate 250 uL...")
        drv.aspirate(250.0)
        log.info("Aspirated 250 uL.")

        input(">>> Observe larger amount. Press Enter to dispense...")
        drv.dispense()

        # ---- Speed control ----
        log.info("")
        log.info("=" * 60)
        log.info("TEST 3: Speed control — aspirate at speed 1 vs 3")
        log.info("=" * 60)

        drv.set_speed(KeyAction.SUCK, 1)
        drv.set_speed(KeyAction.BLOW, 1)
        drv.set_volume(200.0)

        input(">>> Press Enter to aspirate at SLOW speed (1)...")
        drv.aspirate()
        log.info("Slow aspirate done.")

        input(">>> Press Enter to dispense (slow)...")
        drv.dispense()

        drv.set_speed(KeyAction.SUCK, 3)
        drv.set_speed(KeyAction.BLOW, 3)

        input(">>> Press Enter to aspirate at FAST speed (3)...")
        drv.aspirate()
        log.info("Fast aspirate done.")

        input(">>> Press Enter to dispense (fast)...")
        drv.dispense()

        # ---- Mixing ----
        log.info("")
        log.info("=" * 60)
        log.info("TEST 4: Mix — 100 uL, 3 cycles, speed 3")
        log.info("=" * 60)
        input(">>> Tip in liquid, press Enter to mix...")

        drv.mix(100.0, cycles=3, speed=3)
        input(">>> Mix done. WITHDRAW TIP from liquid now, then press Enter...")
        log.info("Mix complete.")

        # ---- Splitting ----
        log.info("")
        log.info("=" * 60)
        log.info("TEST 5: Split — 100 uL x 3 aliquots")
        log.info("=" * 60)
        input(">>> Tip in liquid, press Enter to start split...")

        drv.split(100.0, count=3)
        input(">>> Split done. WITHDRAW TIP from liquid now, then press Enter...")
        log.info("Split complete.")

        # ---- Dilution ----
        log.info("")
        log.info("=" * 60)
        log.info("TEST 6: Dilution — vol1=200 uL, vol2=100 uL")
        log.info("=" * 60)
        input(">>> Tip in liquid, press Enter to start dilution...")

        drv.dilute(200.0, 100.0)
        input(">>> Dilution done. WITHDRAW TIP from liquid now, then press Enter...")
        log.info("Dilution complete.")

        # ---- Done ----
        log.info("")
        log.info("=" * 60)
        log.info("ALL TESTS COMPLETE")
        log.info("=" * 60)

    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        drv.disconnect()


if __name__ == "__main__":
    main()
