#!/usr/bin/env python3
"""Volume-controlled pipetting — set volume via serial, no hardware mods.

Demonstrates changing the aspiration volume between cycles using B2
(PI_VOLUM). The volume is controlled entirely via serial commands.

Usage:
    python examples/volume_control.py
"""

from dpette.config import SerialConfig, guess_default_port
from dpette.driver import DPetteDriver


def main() -> None:
    port = guess_default_port() or "/dev/cu.usbserial-0001"
    cfg = SerialConfig(port=port)
    driver = DPetteDriver(cfg)

    print(f"Connecting to dPette on {port}...")
    driver.connect()

    volumes = [50, 100, 200]
    for vol in volumes:
        input(f"\nPress Enter to aspirate {vol} µL...")
        driver.aspirate(float(vol))
        print(f"Aspirated {vol} µL.")

        input("Press Enter to dispense...")
        driver.dispense()
        print("Dispensed.")

    driver.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    main()
