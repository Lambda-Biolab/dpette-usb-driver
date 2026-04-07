#!/usr/bin/env python3
"""Send protocol probes with confirmed byte constants from disassembly.

From PetteCali.exe disassembly (confirmed at instruction level):
  HEADER        = 0xFE
  CMD_HANDSHAKE = 0xA5
  CMD_READ_EE   = 0xA6
  CMD_WRITE_EE  = 0xA4

All packets are 6 bytes (NOT 7 as originally assumed):

  HandShake: [0xFE] [0xA5] [param] [0x00] [0x00] [CHECKSUM]
  ReadEE:    [0xFE] [0xA6] [addr_hi] [addr_lo] [0x00] [CHECKSUM]
  WriteEE:   [0xFE] [0xA4] [addr_hi] [addr_lo] [value] [CHECKSUM]

Checksum = sum(bytes[1:5]) & 0xFF  (bytes 1 through 4 inclusive)
"""

import argparse
import time

import serial

HEADER = 0xFE
CMD_HANDSHAKE = 0xA5
CMD_READ_EE = 0xA6
CMD_WRITE_EE = 0xA4


def checksum(data: bytes) -> int:
    """Byte sum of bytes[1:5], truncated to 8 bits."""
    return sum(data[1:5]) & 0xFF


def make_handshake(param: int = 0) -> bytes:
    pkt = bytes([HEADER, CMD_HANDSHAKE, param, 0x00, 0x00])
    return pkt + bytes([checksum(pkt)])


def make_read_ee(addr: int) -> bytes:
    addr_hi = (addr >> 8) & 0xFF
    addr_lo = addr & 0xFF
    pkt = bytes([HEADER, CMD_READ_EE, addr_hi, addr_lo, 0x00])
    return pkt + bytes([checksum(pkt)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe dPette with confirmed protocol")
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()

    ser = serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    )
    ser.reset_input_buffer()

    probes = [
        ("HandShake param=0", make_handshake(0)),
        ("HandShake param=1 (DPETTE)", make_handshake(1)),
        ("HandShake param=2 (DPETTE+)", make_handshake(2)),
        ("HandShake param=3 (DPETTE+8)", make_handshake(3)),
        ("HandShake param=4 (PETTE)", make_handshake(4)),
        ("HandShake param=5 (PETTEMULTI)", make_handshake(5)),
        ("ReadEE 0x0080 (cal point count)", make_read_ee(0x0080)),
        ("ReadEE 0x0082 (cal volume 1)", make_read_ee(0x0082)),
        ("ReadEE 0x0090 (seg1 k byte0)", make_read_ee(0x0090)),
    ]

    print(f"Port: {args.port} @ {args.baud} baud")
    print(f"Timeout: {args.timeout}s per probe")
    print("HEADER=0xFE | 6-byte packets | cksum=sum(bytes[1:5])&0xFF")
    print("Make sure pipette is AWAKE (press button)!")
    print("-" * 60)

    for name, pkt in probes:
        ser.reset_input_buffer()
        hex_tx = pkt.hex(" ")
        print(f"\n>>> {name}")
        print(f"    TX ({len(pkt)} bytes): {hex_tx}")

        ser.write(pkt)
        ser.flush()

        resp = ser.read(64)

        if resp:
            hex_rx = resp.hex(" ")
            ascii_rx = "".join(chr(b) if 32 <= b < 127 else "." for b in resp)
            print(f"    RX ({len(resp)} bytes): {hex_rx}")
            print(f"    ASCII: {ascii_rx}")
        else:
            print("    RX: (no response)")

        time.sleep(0.2)

    ser.close()
    print("\n" + "-" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
