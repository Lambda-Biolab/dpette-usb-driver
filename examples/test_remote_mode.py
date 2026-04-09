#!/usr/bin/env python3
"""EXP-049: Test the official DLAB remote control protocol.

The official Communication_Protocol_CN.doc (from xg590/Learn_dPettePlus)
reveals a completely different workflow from what we've been using:

  Our flow:     A5 (handshake) -> B0 b2=1 (dispense) -> B3 b2=1 (aspirate)
  Official:     A0 (handshake) -> B0 b2=1 (enter PI mode) -> B2 (set vol) -> B3 b2=1/2 (suck/blow)

Key differences:
  - A0 is the real handshake (not A5, which is calibration mode entry)
  - B0 param=1 is "enter PI (pipetting) mode", not "dispense"
  - B2 sets pipetting volume (24-bit big-endian, volume * 100)
  - B3 b2=2 is dispense (we never tried this!)

This script tests the full official protocol sequence and logs every
byte exchanged, so we can see exactly what the device supports.

Usage:
    python examples/test_remote_mode.py [--port /dev/cu.usbserial-0001]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

# -- minimal protocol helpers (no dependency on dpette.protocol) -----------
# We define these inline so the script is self-contained and we can test
# encodings that differ from the existing driver.

HEADER_TX = 0xFE
HEADER_RX = 0xFD


def _cksum(cmd: int, b2: int, b3: int, b4: int) -> int:
    return (cmd + b2 + b3 + b4) & 0xFF


def _pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    return bytes([HEADER_TX, cmd, b2, b3, b4, _cksum(cmd, b2, b3, b4)])


def _hex(data: bytes) -> str:
    return data.hex(" ") if data else "(empty)"


def _desc_rx(data: bytes) -> str:
    """Describe a 6-byte response."""
    if len(data) < 6:
        return f"SHORT ({len(data)} bytes): {_hex(data)}"
    hdr, cmd, p1, p2, p3, ck = data[:6]
    expected_ck = (cmd + p1 + p2 + p3) & 0xFF
    ck_ok = "OK" if ck == expected_ck else f"BAD (expected {expected_ck:02x})"
    return (
        f"[{hdr:02x}] cmd={cmd:02x} p1={p1:02x} p2={p2:02x} p3={p3:02x} "
        f"ck={ck:02x}({ck_ok})"
    )


# -- volume encoding per official doc: volume * 100, 24-bit big-endian ----


def _vol_b2(vol_ul: int) -> tuple[int, int, int]:
    """Encode volume for B2 (PI_VOLUM): volume * 100 across 3 bytes."""
    v = vol_ul * 100
    return ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)


# -- test harness ----------------------------------------------------------


class RemoteModeTest:
    def __init__(self, port: str, timeout: float = 2.0):
        import serial

        self.port_name = port
        self.ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
        )
        self.log = logging.getLogger("EXP-049")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send(
        self, label: str, pkt: bytes, read_bytes: int = 6, pause: float = 0.5
    ) -> bytes:
        """Send a packet, read response, log everything."""
        self.log.info("--- %s ---", label)
        self.log.info("  TX: %s", _hex(pkt))
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        self.ser.flush()
        time.sleep(pause)
        resp = self.ser.read(read_bytes)
        if resp:
            # Log each 6-byte frame separately
            for i in range(0, len(resp), 6):
                chunk = resp[i : i + 6]
                self.log.info("  RX[%d]: %s  %s", i // 6, _hex(chunk), _desc_rx(chunk))
        else:
            self.log.info("  RX: (no response)")
        return resp

    def drain(self):
        """Read and discard any pending bytes."""
        leftover = self.ser.read(256)
        if leftover:
            self.log.info(
                "  (drained %d leftover bytes: %s)", len(leftover), _hex(leftover)
            )

    def run(self, test_volume_ul: int = 200):
        self.log.info("=" * 60)
        self.log.info("EXP-049: Official DLAB remote control protocol test")
        self.log.info("Port: %s  |  Test volume: %d uL", self.port_name, test_volume_ul)
        self.log.info("=" * 60)

        # ---- Phase 1: Official handshake (A0) ----
        self.log.info("")
        self.log.info("==== PHASE 1: Handshake ====")

        r = self.send("A0 HELLO (official handshake)", _pkt(0xA0))
        a0_works = len(r) >= 6 and r[0] == HEADER_RX

        r = self.send("A5 b2=0 (our current 'handshake')", _pkt(0xA5, 0x00))
        a5_works = len(r) >= 6 and r[0] == HEADER_RX

        self.log.info("")
        self.log.info("A0 responds: %s  |  A5 responds: %s", a0_works, a5_works)

        # ---- Phase 2: Enter PI remote mode (B0 param=1) ----
        self.log.info("")
        self.log.info("==== PHASE 2: Enter PI mode (B0 param=1) ====")
        self.log.info("Official doc says this enters pipetting mode + motor homes.")
        self.log.info("We previously interpreted this as 'dispense'.")

        r = self.send("B0 param=1 (enter PI mode)", _pkt(0xB0, 0x01), pause=2.0)
        b0_success = len(r) >= 6 and r[0] == HEADER_RX and r[2] == 0x00
        self.log.info("B0 accepted (p1=0): %s", b0_success)
        self.drain()

        # ---- Phase 3: Set speed (B1) ----
        self.log.info("")
        self.log.info("==== PHASE 3: Set speed (B1) ====")

        r = self.send("B1 aspirate speed=2", _pkt(0xB1, 0x01, 0x02))
        b1_suck = len(r) >= 6 and r[0] == HEADER_RX and r[2] == 0x00

        r = self.send("B1 dispense speed=2", _pkt(0xB1, 0x02, 0x02))
        b1_blow = len(r) >= 6 and r[0] == HEADER_RX and r[2] == 0x00

        self.log.info(
            "B1 suck speed accepted: %s  |  B1 blow speed accepted: %s",
            b1_suck,
            b1_blow,
        )

        # ---- Phase 4: Set volume via B2 (PI_VOLUM) ----
        self.log.info("")
        self.log.info("==== PHASE 4: Set volume via B2 (PI_VOLUM) ====")
        hi, mid, lo = _vol_b2(test_volume_ul)
        self.log.info(
            "Volume %d uL -> %d (x100) -> bytes: %02x %02x %02x",
            test_volume_ul,
            test_volume_ul * 100,
            hi,
            mid,
            lo,
        )

        r = self.send(
            f"B2 PI_VOLUM = {test_volume_ul} uL",
            _pkt(0xB2, hi, mid, lo),
        )
        b2_success = len(r) >= 6 and r[0] == HEADER_RX and r[2] == 0x00
        self.log.info("B2 accepted (p1=0): %s", b2_success)

        # ---- Phase 5: Aspirate via B3 b2=1 ----
        self.log.info("")
        self.log.info("==== PHASE 5: Aspirate (B3 param=1) ====")
        self.log.info("Official doc says two responses: ACK then completion.")

        input(">>> Tip attached and ready? Press Enter to aspirate...")

        r = self.send(
            "B3 param=1 (ASPIRATE)", _pkt(0xB3, 0x01), read_bytes=12, pause=5.0
        )
        b3_suck_len = len(r)
        self.log.info("B3 aspirate response length: %d bytes", b3_suck_len)
        self.drain()

        # ---- Phase 6: Dispense via B3 b2=2 ----
        self.log.info("")
        self.log.info("==== PHASE 6: Dispense (B3 param=2) ====")
        self.log.info("Official doc: b2=2 for blow. We've NEVER tested this.")

        input(">>> Press Enter to dispense...")

        r = self.send(
            "B3 param=2 (DISPENSE)", _pkt(0xB3, 0x02), read_bytes=12, pause=5.0
        )
        b3_blow_len = len(r)
        self.log.info("B3 dispense response length: %d bytes", b3_blow_len)
        self.drain()

        # ---- Phase 7: Fallback — test B2 + our known-working flow ----
        self.log.info("")
        self.log.info("==== PHASE 7: B2 volume + our known flow (B0 prime -> B3) ====")
        self.log.info("If phases 5-6 failed, test whether B2 affects the known flow.")

        # Re-send B2 volume
        self.send(
            f"B2 PI_VOLUM = {test_volume_ul} uL (re-send)", _pkt(0xB2, hi, mid, lo)
        )

        # Prime with B0 (our known working method)
        self.send("B0 b2=1 (prime/home)", _pkt(0xB0, 0x01), pause=2.0)
        self.drain()

        input(">>> Press Enter to aspirate via B3 (after B2 + B0 prime)...")
        r = self.send(
            "B3 param=1 (aspirate after B2+B0)",
            _pkt(0xB3, 0x01),
            read_bytes=12,
            pause=5.0,
        )
        self.drain()

        # ---- Summary ----
        self.log.info("")
        self.log.info("=" * 60)
        self.log.info("SUMMARY")
        self.log.info("=" * 60)
        self.log.info("A0 handshake responds:   %s", a0_works)
        self.log.info("B0 PI mode accepted:     %s", b0_success)
        self.log.info("B1 speed accepted:       suck=%s  blow=%s", b1_suck, b1_blow)
        self.log.info("B2 volume accepted:      %s", b2_success)
        self.log.info(
            "B3 aspirate bytes:       %d  (expect 12 if motor moved)", b3_suck_len
        )
        self.log.info(
            "B3 dispense bytes:       %d  (expect 12 if motor moved)", b3_blow_len
        )
        self.log.info("")
        self.log.info("If B3 gave 12 bytes in phase 5, the official remote")
        self.log.info("protocol works. Measure the liquid to check if B2")
        self.log.info("volume was respected vs the dial volume.")
        self.log.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="EXP-049: Test DLAB remote control protocol"
    )
    parser.add_argument(
        "--port", default=None, help="Serial port (auto-detected if omitted)"
    )
    parser.add_argument(
        "--volume", type=int, default=200, help="Test volume in uL (default: 200)"
    )
    args = parser.parse_args()

    # Setup logging: console + file
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("captures/exp049_remote_mode.log", mode="w"),
        ],
    )

    port = args.port
    if port is None:
        from dpette.config import guess_default_port

        port = guess_default_port()
    if port is None:
        print("ERROR: No serial port found. Use --port to specify.", file=sys.stderr)
        sys.exit(1)

    t = RemoteModeTest(port)
    try:
        t.run(test_volume_ul=args.volume)
    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        t.close()


if __name__ == "__main__":
    main()
