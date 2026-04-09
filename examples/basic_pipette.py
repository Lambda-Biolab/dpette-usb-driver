#!/usr/bin/env python3
"""Basic pipette control — aspirate and dispense at a set volume.

Usage:
    python examples/basic_pipette.py
"""

from dpette.config import SerialConfig, guess_default_port
from dpette.driver import DPetteDriver


def main() -> None:
    port = guess_default_port() or "/dev/cu.usbserial-0001"

    print(f"Connecting to dPette on {port}...")
    cfg = SerialConfig(port=port)
    driver = DPetteDriver(cfg)

    driver.connect()
    print("Connected!")

    print("Aspirating 200 µL...")
    driver.aspirate(200.0)

    input("Press Enter to dispense...")

    print("Dispensing...")
    driver.dispense()

    driver.disconnect()
    print("Done.")


if __name__ == "__main__":
    main()
