#!/usr/bin/env python3
"""EXP-051: Mixing test — rapid aspirate/dispense cycles at max speed.

Tests how fast the device can cycle B3 suck/blow in PI mode.
Measures actual motor travel time per cycle at speed 1, 2, and 3.

Usage:
    python examples/test_mix.py [--port /dev/cu.usbserial-0001] [--volume 100] [--cycles 3]
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


class MixTest:
    def __init__(self, port, timeout=10.0):
        import serial

        self.ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
        )
        self.log = logging.getLogger("EXP-051")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send(self, label, pkt, read_bytes=12):
        """Send packet, wait for full response, return (response, elapsed_seconds)."""
        self.log.info("--- %s ---", label)
        self.log.info("  TX: %s", _hex(pkt))
        self.ser.reset_input_buffer()
        t0 = time.monotonic()
        self.ser.write(pkt)
        self.ser.flush()
        resp = self.ser.read(read_bytes)
        elapsed = time.monotonic() - t0
        for i in range(0, len(resp), 6):
            chunk = resp[i : i + 6]
            self.log.info("  RX[%d]: %s", i // 6, _hex(chunk))
        if not resp:
            self.log.info("  RX: (no response)")
        self.log.info("  elapsed: %.2fs", elapsed)
        return resp, elapsed

    def send_short(self, label, pkt):
        """Send packet expecting a single 6-byte ACK."""
        self.log.info("--- %s ---", label)
        self.log.info("  TX: %s", _hex(pkt))
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        self.ser.flush()
        time.sleep(0.3)
        resp = self.ser.read(6)
        if resp:
            self.log.info("  RX: %s", _hex(resp))
        return resp

    def drain(self):
        leftover = self.ser.read(256)
        if leftover:
            self.log.info("  (drained %d bytes)", len(leftover))

    def mix_at_speed(self, speed, volume_ul, cycles):
        """Run mix cycles at a given speed. Returns list of cycle times."""
        self.log.info("")
        self.log.info(
            "==== MIX: speed=%d, volume=%d uL, cycles=%d ====", speed, volume_ul, cycles
        )

        # Set speed
        self.send_short(f"B1 suck speed={speed}", _pkt(0xB1, 0x01, speed))
        self.send_short(f"B1 blow speed={speed}", _pkt(0xB1, 0x02, speed))

        # Set volume
        hi, mid, lo = _vol_b2(volume_ul)
        self.send_short(f"B2 = {volume_ul} uL", _pkt(0xB2, hi, mid, lo))

        cycle_times = []
        for i in range(1, cycles + 1):
            self.log.info("")
            self.log.info("---- Cycle %d/%d (speed=%d) ----", i, cycles, speed)

            t_cycle_start = time.monotonic()

            _, t_suck = self.send(f"B3 SUCK (cycle {i})", _pkt(0xB3, 0x01))
            _, t_blow = self.send(f"B3 BLOW (cycle {i})", _pkt(0xB3, 0x02))

            t_cycle = time.monotonic() - t_cycle_start
            cycle_times.append(t_cycle)

            self.log.info(
                "  cycle %d: suck=%.2fs  blow=%.2fs  total=%.2fs",
                i,
                t_suck,
                t_blow,
                t_cycle,
            )

        avg = sum(cycle_times) / len(cycle_times) if cycle_times else 0
        self.log.info("")
        self.log.info(
            "Speed %d summary: avg cycle=%.2fs, total=%.2fs for %d cycles",
            speed,
            avg,
            sum(cycle_times),
            cycles,
        )
        return cycle_times

    def run(self, volume_ul, cycles):
        self.log.info("=" * 60)
        self.log.info("EXP-051: Mixing test — aspirate/dispense cycle timing")
        self.log.info("Volume: %d uL  |  Cycles per speed: %d", volume_ul, cycles)
        self.log.info("=" * 60)

        # Setup
        self.send_short("A0 HELLO", _pkt(0xA0))
        r, _ = self.send("B0 enter PI mode", _pkt(0xB0, 0x01))
        self.drain()

        input(">>> Tip in liquid and ready? Press Enter to start mixing...")

        all_results = {}
        for speed in [1, 2, 3]:
            times = self.mix_at_speed(speed, volume_ul, cycles)
            all_results[speed] = times

            if speed < 3:
                input(f">>> Speed {speed} done. Press Enter for speed {speed+1}...")

        # Summary
        self.log.info("")
        self.log.info("=" * 60)
        self.log.info("TIMING SUMMARY")
        self.log.info("=" * 60)
        self.log.info(
            "%-8s  %-12s  %-12s  %s", "Speed", "Avg cycle", "Total", "Per-cycle"
        )
        for speed, times in all_results.items():
            avg = sum(times) / len(times)
            detail = ", ".join(f"{t:.2f}s" for t in times)
            self.log.info(
                "%-8d  %-12.2fs  %-12.2fs  %s", speed, avg, sum(times), detail
            )

        fastest = min(all_results.items(), key=lambda x: sum(x[1]) / len(x[1]))
        self.log.info("")
        self.log.info(
            "Fastest: speed=%d at %.2fs/cycle",
            fastest[0],
            sum(fastest[1]) / len(fastest[1]),
        )
        self.log.info(
            "A %d-cycle mix at speed %d takes ~%.1fs total",
            cycles,
            fastest[0],
            sum(fastest[1]),
        )
        self.log.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="EXP-051: Mixing cycle timing test")
    parser.add_argument("--port", default=None)
    parser.add_argument(
        "--volume", type=int, default=100, help="Mix volume in uL (default: 100)"
    )
    parser.add_argument(
        "--cycles", type=int, default=3, help="Cycles per speed level (default: 3)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("captures/exp051_mix.log", mode="w"),
        ],
    )

    port = args.port
    if port is None:
        from dpette.config import guess_default_port

        port = guess_default_port()
    if port is None:
        print("ERROR: No serial port found.", file=sys.stderr)
        sys.exit(1)

    t = MixTest(port)
    try:
        t.run(volume_ul=args.volume, cycles=args.cycles)
    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        t.close()


if __name__ == "__main__":
    main()
