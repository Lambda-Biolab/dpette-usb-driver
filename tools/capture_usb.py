#!/usr/bin/env python3
"""Instructions and helpers for capturing USB traffic with USBPcap / Wireshark.

This script does NOT perform OS-level USB capture itself.  Instead it
prints step-by-step instructions for the operator and validates that
capture files land in the right place.

Usage::

    python tools/capture_usb.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

CAPTURES_DIR = Path(__file__).resolve().parent.parent / "captures"

INSTRUCTIONS = """\
=== dPette USB Capture Guide ===

1. PREREQUISITES
   - Windows: install USBPcap (https://desowin.org/usbpcap/) and Wireshark.
   - Linux:   modprobe usbmon; use Wireshark or tshark on usbmonN interface.
   - macOS:   USB capture requires a VM or a Linux machine.

2. IDENTIFY THE DEVICE
   - Plug in the dPette via USB.
   - In Wireshark, look for a new USB device on the capture interface.
   - Note the bus/device numbers.

3. START CAPTURE
   - Filter to the specific device to reduce noise.
   - Start capture BEFORE launching the vendor calibration software.

4. PERFORM OPERATIONS
   - Launch the DLAB calibration tool.
   - Connect to the pipette.
   - Perform: identify, set volume, aspirate, dispense, blow-out, eject.
   - Pause briefly between each operation for easy segmentation.

5. SAVE THE CAPTURE
   - Stop the capture in Wireshark.
   - Export as .pcapng (preferred) or .pcap.
   - Save to: {captures_dir}/

   Naming convention:
       YYYY-MM-DD_<operation>_<baud-if-known>.pcapng
   Example:
       2026-04-06_full-session_unknown-baud.pcapng

6. ANALYSING CAPTURES
   - In Wireshark, filter: usb.transfer_type == 0x03 (bulk transfers)
   - Look at the data payload of URB_BULK out/in for serial bytes.
   - Document findings in docs/PROTOCOL_NOTES.md.
"""


def main() -> None:
    print(INSTRUCTIONS.format(captures_dir=CAPTURES_DIR))

    suggested = CAPTURES_DIR / f"{datetime.now():%Y-%m-%d}_session.pcapng"
    print(f"Suggested filename: {suggested}")
    print(f"Captures directory: {CAPTURES_DIR}")

    if not CAPTURES_DIR.exists():
        CAPTURES_DIR.mkdir(parents=True)
        print("Created captures/ directory.")

    existing = list(CAPTURES_DIR.glob("*.pcap*"))
    if existing:
        print(f"\nExisting captures ({len(existing)}):")
        for f in sorted(existing):
            print(f"  - {f.name}  ({f.stat().st_size / 1024:.1f} KB)")
    else:
        print("\nNo captures found yet.")


if __name__ == "__main__":
    main()
