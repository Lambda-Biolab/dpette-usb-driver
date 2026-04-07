#!/usr/bin/env python3
"""EEPROM write-read test at address 0x88 (unused cal volume 4).

Tests multiple write/read format hypotheses to find the correct one.
After testing, restores original value.

Run directly:
    python tools/eeprom_write_read.py
"""

import time

import serial

HEADER_TX = 0xFE
PORT = "/dev/cu.usbserial-0001"
TEST_ADDR = 0x88
TEST_VAL = 0x42


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, cmd, b2, b3, b4])
    return pkt + bytes([checksum(pkt)])


def send_recv(ser: serial.Serial, pkt: bytes, wait: float = 0.5) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


def read_addr(ser: serial.Serial, addr: int, label: str) -> None:
    """Try reading an address with multiple CMD/format hypotheses."""
    print(f"  [{label}] Reading addr 0x{addr:02X}:")

    # Hypothesis 1: CMD=0xA6 with addr in b2 (SendCaliVolume format)
    resp = send_recv(ser, make_pkt(0xA6, addr), wait=0.3)
    print(f"    A6 b2=addr:     RX ({len(resp):2d}b) {resp.hex(' ')}")

    # Hypothesis 2: CMD=0xA4 with addr in b2, val=0 (WriteEE as read?)
    resp = send_recv(ser, make_pkt(0xA4, addr, 0x00, 0x00), wait=0.3)
    print(f"    A4 b2=addr:     RX ({len(resp):2d}b) {resp.hex(' ')}")

    # Hypothesis 3: CMD=0xA3 with addr in b2
    resp = send_recv(ser, make_pkt(0xA3, addr), wait=0.3)
    print(f"    A3 b2=addr:     RX ({len(resp):2d}b) {resp.hex(' ')}")

    # Hypothesis 4: CMD=0xA1 (13-byte bulk read)
    resp = send_recv(ser, make_pkt(0xA1), wait=0.3)
    print(f"    A1 bulk:        RX ({len(resp):2d}b) {resp.hex(' ')}")

    # Hypothesis 5: CMD=0xA2 (13-byte bulk read)
    resp = send_recv(ser, make_pkt(0xA2), wait=0.3)
    print(f"    A2 bulk:        RX ({len(resp):2d}b) {resp.hex(' ')}")


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

# Handshake
resp = send_recv(ser, make_pkt(0xA5))
print(f"Handshake: {resp.hex(' ')}\n")

# Step 1: Read baseline
print("=" * 60)
print(f"STEP 1: BASELINE READ of addr 0x{TEST_ADDR:02X}")
read_addr(ser, TEST_ADDR, "baseline")

# Step 2: Write test value using multiple format hypotheses
print(f"\n{'=' * 60}")
print(f"STEP 2: WRITE 0x{TEST_VAL:02X} to addr 0x{TEST_ADDR:02X}")
print()

# Write hypothesis A: A4 b2=addr b3=0 b4=val
pkt = make_pkt(0xA4, TEST_ADDR, 0x00, TEST_VAL)
resp = send_recv(ser, pkt, wait=0.5)
print(
    f"  Write A (A4 addr,0,val): TX {pkt.hex(' ')} → RX ({len(resp):2d}b) {resp.hex(' ') if resp else '(none)'}"
)

# Read back after write A
print()
read_addr(ser, TEST_ADDR, "after write-A")

# Write hypothesis B: A4 b2=addr b3=val b4=0
pkt = make_pkt(0xA4, TEST_ADDR, TEST_VAL, 0x00)
resp = send_recv(ser, pkt, wait=0.5)
print(
    f"\n  Write B (A4 addr,val,0): TX {pkt.hex(' ')} → RX ({len(resp):2d}b) {resp.hex(' ') if resp else '(none)'}"
)

# Read back after write B
print()
read_addr(ser, TEST_ADDR, "after write-B")

# Write hypothesis C: A4 b2=0 b3=addr b4=val (2-byte address format)
pkt = make_pkt(0xA4, 0x00, TEST_ADDR, TEST_VAL)
resp = send_recv(ser, pkt, wait=0.5)
print(
    f"\n  Write C (A4 0,addr,val): TX {pkt.hex(' ')} → RX ({len(resp):2d}b) {resp.hex(' ') if resp else '(none)'}"
)

# Read back after write C
print()
read_addr(ser, TEST_ADDR, "after write-C")

# Step 3: Restore original value (0x00)
print(f"\n{'=' * 60}")
print(f"STEP 3: RESTORE addr 0x{TEST_ADDR:02X} to 0x00")
for b2, b3, b4, label in [
    (TEST_ADDR, 0x00, 0x00, "A4 addr,0,0"),
    (0x00, TEST_ADDR, 0x00, "A4 0,addr,0"),
]:
    pkt = make_pkt(0xA4, b2, b3, b4)
    resp = send_recv(ser, pkt, wait=0.3)
    print(
        f"  {label}: TX {pkt.hex(' ')} → RX ({len(resp):2d}b) {resp.hex(' ') if resp else '(none)'}"
    )

# Final read
print()
read_addr(ser, TEST_ADDR, "final")

ser.close()
print(f"\n{'=' * 60}")
print("Done.")
