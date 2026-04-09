#!/usr/bin/env python3
"""EXP-050: B2 volume control verification — does B2 actually change motor travel?

Dial stays at 300 uL. We send B2 at 50 uL then 200 uL and aspirate each.
If both draw 300 uL worth of liquid, B2 is cosmetic only.
If they draw visibly different amounts matching 50 and 200, volume control works.

Usage:
    python examples/test_b2_volume.py [--port /dev/cu.usbserial-0001]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

HEADER_TX = 0xFE
HEADER_RX = 0xFD


def _ck(cmd, b2, b3, b4):
    return (cmd + b2 + b3 + b4) & 0xFF


def _pkt(cmd, b2=0, b3=0, b4=0):
    return bytes([HEADER_TX, cmd, b2, b3, b4, _ck(cmd, b2, b3, b4)])


def _hex(d):
    return d.hex(" ") if d else "(empty)"


def _vol_b2(vol_ul):
    v = vol_ul * 100
    return ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)


class VolumeTest:
    def __init__(self, port, timeout=2.0):
        import serial

        self.ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
        )
        self.log = logging.getLogger("EXP-050")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send(self, label, pkt, read_bytes=6, pause=0.5):
        self.log.info("--- %s ---", label)
        self.log.info("  TX: %s", _hex(pkt))
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        self.ser.flush()
        time.sleep(pause)
        resp = self.ser.read(read_bytes)
        for i in range(0, len(resp), 6):
            chunk = resp[i : i + 6]
            self.log.info("  RX[%d]: %s", i // 6, _hex(chunk))
        if not resp:
            self.log.info("  RX: (no response)")
        return resp

    def drain(self):
        leftover = self.ser.read(256)
        if leftover:
            self.log.info("  (drained %d bytes)", len(leftover))

    def aspirate_at_volume(self, vol_ul):
        """Send B2 to set volume, then B3 b2=1 to aspirate. Return response length."""
        hi, mid, lo = _vol_b2(vol_ul)
        self.log.info("")
        self.log.info("==== ASPIRATE at B2 = %d uL (dial = 300) ====", vol_ul)
        self.log.info(
            "B2 encoding: %d * 100 = %d -> %02x %02x %02x",
            vol_ul,
            vol_ul * 100,
            hi,
            mid,
            lo,
        )

        self.send(f"B2 = {vol_ul} uL", _pkt(0xB2, hi, mid, lo))

        input(f">>> B2 set to {vol_ul} uL. Press Enter to aspirate...")

        r = self.send(
            f"B3 ASPIRATE (expecting {vol_ul} uL)",
            _pkt(0xB3, 0x01),
            read_bytes=12,
            pause=5.0,
        )
        self.drain()

        motor_moved = len(r) >= 12
        self.log.info("Motor moved: %s (%d bytes)", motor_moved, len(r))
        return motor_moved

    def dispense(self):
        """B3 b2=2 dispense."""
        input(">>> Press Enter to dispense...")
        self.send("B3 DISPENSE", _pkt(0xB3, 0x02), read_bytes=12, pause=5.0)
        self.drain()

    def run(self):
        self.log.info("=" * 60)
        self.log.info("EXP-050: B2 volume control — 50 vs 200 uL (dial at 300)")
        self.log.info("=" * 60)

        # Setup: A0 handshake + B0 PI mode
        self.send("A0 HELLO", _pkt(0xA0))
        self.send("B0 enter PI mode", _pkt(0xB0, 0x01), pause=2.0)
        self.drain()

        # ---- Trial 1: 50 uL ----
        self.aspirate_at_volume(50)
        print("\n>>> OBSERVE: Did it draw a SMALL amount (~50 uL)?")
        print(">>>   If it drew the full 300 uL dial amount, B2 is cosmetic.\n")
        self.dispense()

        # ---- Trial 2: 200 uL ----
        self.aspirate_at_volume(200)
        print("\n>>> OBSERVE: Did it draw a MEDIUM amount (~200 uL)?")
        print(">>>   Compare to trial 1. Different = B2 works!\n")
        self.dispense()

        # ---- Trial 3: 50 uL again (confirm repeatability) ----
        self.aspirate_at_volume(50)
        print("\n>>> OBSERVE: Same small amount as trial 1?")
        print(">>>   If yes, B2 volume control is CONFIRMED.\n")
        self.dispense()

        self.log.info("")
        self.log.info("=" * 60)
        self.log.info("DONE — Three trials complete.")
        self.log.info("  Trial 1: B2=50   (expect small)")
        self.log.info("  Trial 2: B2=200  (expect ~4x more)")
        self.log.info("  Trial 3: B2=50   (expect same as trial 1)")
        self.log.info("If all three matched B2 not dial, volume control is SOLVED.")
        self.log.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="EXP-050: B2 volume control test")
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("captures/exp050_b2_volume.log", mode="w"),
        ],
    )

    port = args.port
    if port is None:
        from dpette.config import guess_default_port

        port = guess_default_port()
    if port is None:
        print("ERROR: No serial port found.", file=sys.stderr)
        sys.exit(1)

    t = VolumeTest(port)
    try:
        t.run()
    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        t.close()


if __name__ == "__main__":
    main()
