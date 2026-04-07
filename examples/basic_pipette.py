#!/usr/bin/env python3
"""Basic pipette control — aspirate and dispense at the dial volume.

This is the simplest working example. No calibration mode, no volume
control — just aspirate and dispense at whatever volume the physical
dial is set to.

Prerequisites:
    - dPette connected via USB
    - Dismiss Err4 if showing (hold the pipette button)
    - Tip attached

Usage:
    python examples/basic_pipette.py
"""

from dpette.config import SerialConfig, guess_default_port
from dpette.driver import DPetteDriver


def main() -> None:
    # Auto-detect the serial port, or specify manually
    port = guess_default_port()
    if port is None:
        port = "/dev/cu.usbserial-0001"  # macOS default
        # port = "/dev/ttyUSB0"           # Linux default

    print(f"Connecting to dPette on {port}...")
    cfg = SerialConfig(port=port)
    driver = DPetteDriver(cfg)

    driver.connect()
    print("Connected! (handshake + prime complete)")

    # Aspirate at dial volume
    print("Aspirating...")
    resp = driver.aspirate()
    print(f"  Aspirate response: {resp.raw.hex(' ')}")

    input("Press Enter to dispense...")

    # Dispense
    print("Dispensing...")
    resp = driver.dispense()
    print(f"  Dispense response: {resp.raw.hex(' ')}")

    driver.disconnect()
    print("Done.")


if __name__ == "__main__":
    main()
