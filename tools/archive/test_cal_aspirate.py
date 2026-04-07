#!/usr/bin/env python3
"""Test if cal mode entry triggers aspirate at A6-set volume.

Theory: A5 b2=1 IS the aspirate in cal mode, but only from home position.
Flow: handshake → A6 set vol → A5 b2=1 (aspirates) → observe

Dismiss Err4 before running.
Logs to captures/cal_aspirate_log.txt
"""

import time

import serial

LOGFILE = "/Users/antoniolamb/repos/dpette-usb-driver/captures/cal_aspirate_log.txt"
_log = open(LOGFILE, "w")


def log(msg: str) -> None:
    print(msg)
    _log.write(msg + "\n")
    _log.flush()


def log_input(prompt: str) -> str:
    print(prompt, end="", flush=True)
    _log.write(prompt)
    _log.flush()
    result = input()
    _log.write(result + "\n")
    _log.flush()
    return result


HEADER_TX = 0xFE
PORT = "/dev/cu.usbserial-0001"


def checksum(data: bytes) -> int:
    return sum(data[1:5]) & 0xFF


def make_pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    pkt = bytes([HEADER_TX, cmd, b2, b3, b4])
    return pkt + bytes([checksum(pkt)])


def vol_pkt(vol_ul: int) -> bytes:
    val = vol_ul * 10
    return make_pkt(0xA6, (val >> 8) & 0xFF, val & 0xFF)


def send_recv(ser: serial.Serial, pkt: bytes, wait: float = 0.5) -> bytes:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


ser = serial.Serial(
    port=PORT, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=3.0
)

log("=== CAL MODE ASPIRATE: ENTRY = ASPIRATE? ===\n")

# Test 1: Handshake → set volume BEFORE cal mode → enter cal mode
log("TEST 1: Handshake → A6=100 → enter cal mode")
log("  Does entering cal mode aspirate 100 µL?")
log_input("  Dismiss Err4, press ENTER: ")

resp = send_recv(ser, make_pkt(0xA5, 0x00))
log(f"  Handshake: {resp.hex(' ') if resp else 'FAIL'}")

resp = send_recv(ser, vol_pkt(100), wait=0.5)
log(f"  A6=100: {resp.hex(' ') if resp else '(none)'}")

log_input("  Press ENTER to enter cal mode (WATCH MOTOR): ")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=3.0)
log(f"  A5 b2=1: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = log_input("  Motor moved? How much? ")
log(f"  >> {note}")

# Dispense + exit cal
log_input("  Dismiss Err4 if showing, press ENTER: ")
send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
log("  Dispensed")
send_recv(ser, make_pkt(0xA5, 0x00), wait=1.0)
log("  Exited cal mode")

# Test 2: Same but with A6=200
log("\n" + "=" * 50)
log("TEST 2: Handshake → A6=200 → enter cal mode")
log("  Does entering cal mode aspirate 200 µL?")
log_input("  Dismiss Err4, press ENTER: ")

resp = send_recv(ser, make_pkt(0xA5, 0x00))
log(f"  Handshake: {resp.hex(' ') if resp else 'FAIL'}")

resp = send_recv(ser, vol_pkt(200), wait=0.5)
log(f"  A6=200: {resp.hex(' ') if resp else '(none)'}")

log_input("  Press ENTER to enter cal mode (WATCH MOTOR): ")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=3.0)
log(f"  A5 b2=1: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = log_input("  Motor moved? How much? ")
log(f"  >> {note}")

# Dispense + exit cal
log_input("  Dismiss Err4 if showing, press ENTER: ")
send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
log("  Dispensed")
send_recv(ser, make_pkt(0xA5, 0x00), wait=1.0)
log("  Exited cal mode")

# Test 3: A6=300
log("\n" + "=" * 50)
log("TEST 3: Handshake → A6=300 → enter cal mode")
log_input("  Dismiss Err4, press ENTER: ")

resp = send_recv(ser, make_pkt(0xA5, 0x00))
log(f"  Handshake: {resp.hex(' ') if resp else 'FAIL'}")

resp = send_recv(ser, vol_pkt(300), wait=0.5)
log(f"  A6=300: {resp.hex(' ') if resp else '(none)'}")

log_input("  Press ENTER to enter cal mode (WATCH MOTOR): ")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=3.0)
log(f"  A5 b2=1: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = log_input("  Motor moved? How much? ")
log(f"  >> {note}")

# Test 4: In cal mode, set new vol, re-enter cal
log("\n" + "=" * 50)
log("TEST 4: Stay in cal mode → A6=150 → A5 b2=1 again")
log_input("  Dismiss Err4 if showing, press ENTER: ")

send_recv(ser, make_pkt(0xB0, 0x01), wait=2.0)
log("  Dispensed first")

resp = send_recv(ser, vol_pkt(150), wait=0.5)
log(f"  A6=150: {resp.hex(' ') if resp else '(none)'}")

log_input("  Press ENTER to send A5 b2=1 (WATCH MOTOR): ")
resp = send_recv(ser, make_pkt(0xA5, 0x01), wait=3.0)
log(f"  A5 b2=1: ({len(resp)}b) {resp.hex(' ') if resp else '(none)'}")
note = log_input("  Motor moved? How much? ")
log(f"  >> {note}")

ser.close()
log("\nDone.")
_log.close()
