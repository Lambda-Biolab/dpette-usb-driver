#!/usr/bin/env python3
"""Fix persistent Err4 — dismiss error first, THEN run commands.

Instructions:
1. Plug in pipette
2. Dismiss Err4 by holding the pipette button
3. Wait for normal menu to show
4. THEN run this script

Run directly:
    python tools/fix_err4.py
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


def connect() -> serial.Serial:
    return serial.Serial(
        port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
    )


def send_recv(ser: serial.Serial, pkt: bytes, wait: float = 0.5) -> bytes:
    try:
        ser.reset_input_buffer()
        ser.write(pkt)
        ser.flush()
        time.sleep(wait)
        return ser.read(64)
    except Exception as e:
        print(f"    Serial error: {e}")
        return b""


print("=== ERR4 FIX ===")
print("Make sure you've ALREADY dismissed the Err4 with the button.")
print("The pipette should show the normal volume display.\n")
input("Press ENTER when ready: ")

ser = connect()

# Step 1: Verify connection works
print("[1] Handshake")
resp = send_recv(ser, make_pkt(0xA5, 0x00))
if not resp:
    print("    No response. Reconnecting...")
    ser.close()
    time.sleep(1.0)
    ser = connect()
    resp = send_recv(ser, make_pkt(0xA5, 0x00))
print(f"    RX: {resp.hex(' ') if resp else 'FAILED — is Err4 dismissed?'}")
if not resp:
    ser.close()
    print("Cannot connect. Dismiss Err4 first, then retry.")
    exit(1)

# Step 2: Verify aspirate still works
print("\n[2] Test aspirate")
input("    Press ENTER to aspirate: ")
resp = send_recv(ser, make_pkt(0xB3, 0x01), wait=3.0)
print(f"    RX: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
worked = len(resp) >= 12
print(f"    Motor {'WORKED' if worked else 'DID NOT WORK'}")
if worked:
    note = input("    How much did it draw? ")
    print(f"    >> {note}")

# Step 3: Dispense
print("\n[3] Dispense")
resp = send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
print(f"    RX: {resp.hex(' ') if resp else '(none)'}")

# Step 4: Try to clear the persistent error by writing to EEPROM
# The Err4 flag might be stored at a specific address
print("\n[4] Attempting to clear persistent error flag")
print("    Writing zeros to calibration state addresses...")

# Try various EEPROM addresses that might hold error/state flags
for addr in range(0x80, 0xB0):
    resp = send_recv(ser, make_pkt(0xA4, addr, 0x00, 0x00), wait=0.1)

# Also try the 2-byte address format
for addr in range(0x80, 0xB0):
    resp = send_recv(ser, make_pkt(0xA4, 0x00, addr, 0x00), wait=0.1)

print("    Done writing zeros.")

# Step 5: Try A0 with different values (possible reset command)
print("\n[5] Trying A0 reset variants")
for b2 in range(0x00, 0x10):
    resp = send_recv(ser, make_pkt(0xA0, b2), wait=0.2)
    if resp:
        print(f"    A0 b2=0x{b2:02X}: {resp.hex(' ')}")

# Step 6: Enter and exit cal mode "cleanly" with volume set to 100
print("\n[6] Clean cal mode cycle (set vol=100, exit)")
input("    Press ENTER: ")
send_recv(ser, make_pkt(0xA5, 0x01), wait=2.0)
input("    Dismiss any error, press ENTER when in cal menu: ")
# Set to 100 µL
val = 100 * 10
send_recv(ser, make_pkt(0xA6, (val >> 8) & 0xFF, val & 0xFF), wait=0.5)
print("    Set vol=100")
# Send A3 (might signal "calibration complete")
send_recv(ser, make_pkt(0xA3, 0x00), wait=0.3)
send_recv(ser, make_pkt(0xA3, 0x01), wait=0.3)
# Exit
send_recv(ser, make_pkt(0xA5, 0x00), wait=1.0)
print("    Exited cal mode")
input("    Dismiss any error, press ENTER: ")

ser.close()

print("\n[7] NOW: unplug the pipette, wait 5 seconds, plug it back in.")
input("    Does Err4 still appear on startup? (yes/no): ")

print("\nDone.")
