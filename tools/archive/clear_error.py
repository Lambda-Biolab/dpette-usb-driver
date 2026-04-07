#!/usr/bin/env python3
"""Try to clear the persistent Err4 state.

Attempts multiple reset strategies:
1. Handshake only (clean session)
2. Write zeros to cal-related EEPROM addresses
3. Send A3 (data/reset?) command
4. Send A0 (unknown — might be reset)
5. Enter cal mode and exit with a "proper" sequence

Run directly:
    python tools/clear_error.py
"""

import time

import serial

HEADER_TX = 0xFE
PORT = "/dev/cu.usbserial-0001"


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


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

print("=== ERROR STATE RECOVERY ===\n")
note = input("Is the pipette showing Err4 right now? (yes/no): ")
print(f">> {note}\n")

# Strategy 1: Simple handshake
print("[1] Simple handshake")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
input("    Did Err4 clear? Press ENTER: ")

# Strategy 2: Enter cal mode properly, set display volume back, exit
print("\n[2] Enter cal mode → restore display volume → exit")
input("    Press ENTER to try: ")
send_recv(ser, make_pkt(0xA5, 0x01), wait=2.0)
print("    Entered cal mode")
input("    Clear Err4 with button if needed, press ENTER: ")

# Set volume to 100 (the original display value)
val = 100 * 10
hi = (val >> 8) & 0xFF
lo = val & 0xFF
resp = send_recv(ser, make_pkt(0xA6, hi, lo), wait=0.5)
print(f"    A6=100uL: {resp.hex(' ') if resp else '(none)'}")

# Exit cal mode
send_recv(ser, make_pkt(0xA5, 0x00), wait=1.0)
print("    Exited cal mode")
input("    Clear any error, press ENTER: ")

# Strategy 3: Write zero to EEPROM error flag addresses
print("\n[3] Write zeros to EEPROM addresses 0x80-0x82")
for addr in [0x80, 0x81, 0x82]:
    resp = send_recv(ser, make_pkt(0xA4, addr, 0x00, 0x00), wait=0.3)
    print(f"    A4 addr=0x{addr:02X} val=0: {resp.hex(' ') if resp else '(none)'}")
input("    Any change? Press ENTER: ")

# Strategy 4: Send A0 (unknown — might be reset)
print("\n[4] Send A0 (possible reset)")
resp = send_recv(ser, make_pkt(0xA0, 0x00))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
resp = send_recv(ser, make_pkt(0xA0, 0x01))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
input("    Any change? Press ENTER: ")

# Strategy 5: Send A3 with various params
print("\n[5] Send A3 (possible data reset)")
for b2 in [0x00, 0x01, 0xFF]:
    resp = send_recv(ser, make_pkt(0xA3, b2))
    print(f"    A3 b2=0x{b2:02X}: {resp.hex(' ') if resp else '(none)'}")
input("    Any change? Press ENTER: ")

# Strategy 6: Send A7 (unknown)
print("\n[6] Send A7")
resp = send_recv(ser, make_pkt(0xA7, 0x00))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
resp = send_recv(ser, make_pkt(0xA7, 0x01))
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")
input("    Any change? Press ENTER: ")

# Final: test if aspirate works normally
print("\n[7] Test aspirate")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    Handshake: {resp.hex(' ') if resp else '(none)'}")
input("    Press ENTER to aspirate: ")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"    Aspirate: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = input("    Did it work? ")
print(f"    >> {note}")

resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print(f"    Dispense: {resp.hex(' ') if resp else '(none)'}")

ser.close()
print("\nDone. Does Err4 still appear on reboot?")
