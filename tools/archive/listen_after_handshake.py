#!/usr/bin/env python3
"""Passive listen AFTER handshake — does the pipette send status
bytes when you press the physical aspirate/dispense buttons?

Usage:
    python tools/listen_after_handshake.py --port /dev/cu.usbserial-0001
"""

import argparse
import time

import serial

HEADER_TX = 0xFE


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, cmd, b2, b3, b4])
    return pkt + bytes([checksum(pkt)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--duration", type=int, default=60, help="seconds to listen")
    args = parser.parse_args()

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=0.5,
    )

    # HandShake first
    ser.reset_input_buffer()
    ser.write(make_pkt(0xA5))
    ser.flush()
    resp = ser.read(6)
    print(f"Handshake: {resp.hex(' ') if resp else '(none)'}")
    time.sleep(0.5)
    ser.reset_input_buffer()

    print(f"\nListening for {args.duration}s — press pipette buttons now!")
    print("(aspirate, dispense, blow-out, eject tip, volume change, etc.)")
    print("-" * 60)

    start = time.time()
    total_bytes = 0

    try:
        while time.time() - start < args.duration:
            data = ser.read(256)
            if data:
                elapsed = time.time() - start
                total_bytes += len(data)
                hex_str = data.hex(" ")
                ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
                print(f"[{elapsed:6.1f}s] ({len(data):3d} bytes) {hex_str}")
                print(f"         ASCII: {ascii_str}")
                # Also try to parse as 6-byte packets
                if len(data) >= 6:
                    for i in range(0, len(data) - 5, 6):
                        pkt = data[i : i + 6]
                        if len(pkt) == 6:
                            print(
                                f"         pkt[{i//6}]: hdr=0x{pkt[0]:02X} cmd=0x{pkt[1]:02X} "
                                f"b2=0x{pkt[2]:02X} b3=0x{pkt[3]:02X} b4=0x{pkt[4]:02X} "
                                f"ck=0x{pkt[5]:02X}"
                            )
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        ser.close()

    print("-" * 60)
    print(f"Done. Received {total_bytes} bytes total.")


if __name__ == "__main__":
    main()
