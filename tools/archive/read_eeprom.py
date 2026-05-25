#!/usr/bin/env python3
"""Read the dPette EEPROM after a successful handshake.

Protocol (confirmed from disassembly + live capture):
  TX header = 0xFE, RX header = 0xFD
  CMD_HANDSHAKE = 0xA5
  CMD_READ_EE   = 0xA6
  All packets = 6 bytes
  Checksum = sum(bytes[1:5]) & 0xFF
"""

import argparse
import time

import serial

HEADER_TX = 0xFE
HEADER_RX = 0xFD
CMD_HANDSHAKE = 0xA5
CMD_READ_EE = 0xA6


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_handshake(param: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, CMD_HANDSHAKE, param, 0x00, 0x00])
    return pkt + bytes([checksum(pkt)])


def make_read_ee(addr: int) -> bytes:
    addr_hi = (addr >> 8) & 0xFF
    addr_lo = addr & 0xFF
    pkt = bytes([HEADER_TX, CMD_READ_EE, addr_hi, addr_lo, 0x00])
    return pkt + bytes([checksum(pkt)])


def send_recv(ser: serial.Serial, pkt: bytes, label: str = "") -> bytes | None:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    resp = ser.read(6)
    if resp:
        print(f"  TX: {pkt.hex(' ')}  →  RX: {resp.hex(' ')}  {label}")
    else:
        print(f"  TX: {pkt.hex(' ')}  →  (timeout)  {label}")
    return resp if resp else None


def read_u16(eeprom: dict[int, int], base: int) -> int | None:
    lo = eeprom.get(base)
    hi = eeprom.get(base + 1)
    if lo is None or hi is None:
        return None
    return (hi << 8) | lo


def read_u32(eeprom: dict[int, int], base: int) -> int | None:
    parts = [eeprom.get(base + i) for i in range(4)]
    if any(p is None for p in parts):
        return None
    b0, b1, b2, b3 = parts
    return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0  # type: ignore[operator]


def read_eeprom_map(ser: serial.Serial, addresses: range) -> dict[int, int]:
    eeprom: dict[int, int] = {}
    for addr in addresses:
        resp = send_recv(ser, make_read_ee(addr), f"addr=0x{addr:02X}")
        # Response format: [0xFD] [CMD] [addr_hi] [addr_lo] [VALUE] [CHECKSUM]
        if resp and len(resp) == 6:
            eeprom[addr] = resp[4]
        time.sleep(0.05)
    return eeprom


def _print_pair(eeprom: dict[int, int], label: str, base_k: int, base_b: int) -> None:
    k = read_u32(eeprom, base_k)
    b = read_u32(eeprom, base_b)
    if k is not None:
        print(f"  {label} k (0x{base_k:02X}): {k} (= {k / 10000.0:.4f})")
    if b is not None:
        print(f"  {label} b (0x{base_b:02X}): {b} (= {b / 10000.0:.4f})")


def print_interpreted(eeprom: dict[int, int]) -> None:
    """Decode EEPROM map per PROTOCOL_NOTES.md."""
    print("\nInterpreted values:")

    cal_points = read_u16(eeprom, 0x80)
    if cal_points is not None:
        print(f"  Cal point count (0x80): {cal_points}")

    for i, base in enumerate([0x82, 0x84, 0x86, 0x88, 0x8A, 0x8C]):
        vol = read_u16(eeprom, base)
        if vol is not None:
            print(f"  Cal volume {i + 1} (0x{base:02X}): {vol} (= {vol / 10.0:.1f} µL)")

    for seg, base_k, base_b in [(1, 0x90, 0x94), (2, 0x98, 0x9C)]:
        _print_pair(eeprom, f"Segment {seg}", base_k, base_b)

    for seg, base_k, base_b in [(1, 0xA0, 0xA4), (2, 0xA8, 0xAC)]:
        _print_pair(eeprom, f"Factory seg{seg}", base_k, base_b)


def print_raw_dump(eeprom: dict[int, int]) -> None:
    print("\nRaw bytes:")
    for addr in sorted(eeprom):
        print(f"  0x{addr:02X}: 0x{eeprom[addr]:02X} ({eeprom[addr]:3d})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read dPette EEPROM")
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

    print(f"Port: {args.port} @ {args.baud}")
    print("=" * 70)

    print("\n[1] Handshake")
    if not send_recv(ser, make_handshake(0), "HandShake"):
        print("FAILED — is the pipette awake?")
        ser.close()
        return
    time.sleep(0.1)

    print("\n[2] Reading EEPROM map (0x80–0xAF)")
    eeprom = read_eeprom_map(ser, range(0x80, 0xB0))

    print("\n" + "=" * 70)
    print("[3] EEPROM contents")
    print("-" * 70)

    if not eeprom:
        print("No data read.")
        ser.close()
        return

    print_raw_dump(eeprom)
    print_interpreted(eeprom)

    ser.close()
    print("\n" + "=" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
