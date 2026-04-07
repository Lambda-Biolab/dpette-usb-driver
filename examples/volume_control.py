#!/usr/bin/env python3
"""Volume-controlled pipetting via calibration mode.

This example sets the aspiration volume remotely using A6, then
triggers aspiration with the physical button (or MOSFET actuator).

**Requires:** A way to press the pipette's physical button — either
manually or via a BSS138 MOSFET wired across the button contacts.
See GitHub issue #3 for the MOSFET wiring guide.

WARNING: Entering calibration mode via serial (A5 b2=1) causes
persistent Err4 on reboot. On a fresh device, use the MOSFET to
press the button instead of sending A5 b2=1 via serial.

Usage:
    python examples/volume_control.py
"""

import time

from dpette.config import SerialConfig, guess_default_port
from dpette.protocol import (
    Command,
    encode_packet,
    send_cali_volume_packet,
)
from dpette.serial_link import SerialLink


def main() -> None:
    port = guess_default_port() or "/dev/cu.usbserial-0001"
    cfg = SerialConfig(port=port)
    link = SerialLink(cfg)

    print(f"Connecting to dPette on {port}...")
    link.open()

    # Handshake
    link.write(encode_packet(Command.HANDSHAKE))
    resp = link.read(6)
    print(f"Handshake: {resp.hex(' ')}")

    # Enter calibration mode
    # WARNING: causes persistent Err4 on reboot!
    # On a fresh device, use MOSFET button press instead.
    print("Entering calibration mode...")
    link.write(encode_packet(Command.HANDSHAKE, b2=0x01))
    time.sleep(3.0)
    resp = link.read(6)
    print(f"Enter cal: {resp.hex(' ') if resp else '(no response — dismiss Err4)'}")

    input("Dismiss Err4 if showing, wait for homing. Press Enter...")
    time.sleep(3.0)

    # Set volume and aspirate
    volumes = [100, 200, 300]
    for vol in volumes:
        print(f"\n--- Setting volume to {vol} µL ---")
        link.write(send_cali_volume_packet(vol))
        time.sleep(0.5)
        resp = link.read(6)
        print(f"A6={vol}: {resp.hex(' ') if resp else '(none)'}")

        input(f"Press the PHYSICAL BUTTON to aspirate {vol} µL, then Enter...")

        # Dispense via serial
        print("Dispensing via B0...")
        link.write(encode_packet(Command.DISPENSE, b2=0x01))
        time.sleep(2.0)
        resp = link.read(6)
        print(f"Dispense: {resp.hex(' ') if resp else '(none)'}")

    link.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
