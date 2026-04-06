#!/usr/bin/env python3
"""Visual volume verification — corrected flow.

Enters cal mode FIRST, waits for homing cycle, THEN sets volume with A6,
THEN triggers aspirate by exiting and re-entering cal mode.

Logs to captures/live_log.txt

Run directly:
    python tools/quick_test.py
"""

import time

import serial

LOGFILE = "/Users/antoniolamb/repos/dpette-usb-driver/captures/live_log.txt"
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


ser = serial.Serial(
    port="/dev/cu.usbserial-0001",
    baudrate=9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=3.0,
)


def pkt(cmd, b2=0):
    data = bytes([0xFE, cmd, b2, 0x00, 0x00])
    return data + bytes([(cmd + b2) & 0xFF])


def vol_pkt_full(vol_ul: int) -> bytes:
    val = vol_ul * 10
    hi = (val >> 8) & 0xFF
    lo = val & 0xFF
    data = bytes([0xFE, 0xA6, hi, lo, 0x00])
    return data + bytes([(0xA6 + hi + lo) & 0xFF])


def sr(p, wait=1.0):
    ser.reset_input_buffer()
    ser.write(p)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


log("=== VISUAL VOLUME VERIFICATION (corrected flow) ===")
log("You need: tip on pipette, cup of water")
log("Tests 50 µL then 300 µL — compare water in tip.\n")
log("Flow per cycle:")
log("  1. Handshake")
log("  2. Enter cal mode → wait for homing cycle to finish")
log("  3. A6 sets volume (in cal mode)")
log("  4. Exit cal mode")
log("  5. Re-enter cal mode → should aspirate at A6-set volume")
log("  6. Observe water, dispense, exit\n")

for vol in [50, 300]:
    log(f"{'=' * 50}")
    log(f"CYCLE: Aspirate {vol} µL")
    log(f"{'=' * 50}")

    # Step 1: Handshake
    log_input("\n[1] Dismiss any Err4. Press ENTER to start: ")
    r = sr(pkt(0xA5, 0x00))
    log(f"    Handshake: {r.hex(' ') if r else 'FAIL'}")

    # Step 2: Enter cal mode — triggers homing cycle
    log("\n[2] Entering cal mode (homing cycle will run)...")
    r = sr(pkt(0xA5, 0x01), wait=5.0)
    log(f"    A5 b2=1: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    log("    Waiting 5s for homing cycle to complete...")
    time.sleep(5.0)
    log_input("    Dismiss Err4 with button. Press ENTER when cal menu shows: ")

    # Step 3: Set volume with A6 (now in cal mode, homing done)
    p = vol_pkt_full(vol)
    r = sr(p, wait=0.5)
    log(f"\n[3] A6={vol}uL: TX {p.hex(' ')} → RX {r.hex(' ') if r else '(none)'}")
    log_input(f"    Does display show {vol}? ")

    # Step 4: Dispense to reset piston
    log("\n[4] Dispensing to reset piston...")
    r = sr(pkt(0xB0, 0x01), wait=3.0)
    log(f"    Dispense: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    time.sleep(2.0)

    # Step 5: Now dip tip in water
    log_input("\n[5] Dip tip in water. Press ENTER when submerged: ")

    # Step 6: Exit cal mode
    log("[6] Exiting cal mode...")
    r = sr(pkt(0xA5, 0x00), wait=1.0)
    log(f"    Exit: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    time.sleep(1.0)

    # Step 7: Re-enter cal mode — THIS should aspirate at A6-set volume
    log(f"[7] Re-entering cal mode — should aspirate {vol} µL...")
    r = sr(pkt(0xA5, 0x01), wait=5.0)
    log(f"    A5 b2=1: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    time.sleep(3.0)

    # Step 8: Observe
    note = log_input("\n[8] Dismiss Err4. How much water in the tip? ")
    log(f"    >> {note}")

    # Step 9: Dispense and exit
    log_input("\n[9] Hold over cup. Press ENTER to dispense: ")
    r = sr(pkt(0xB0, 0x01), wait=2.0)
    log(f"    Dispense: {r.hex(' ') if r else '(none)'}")
    r = sr(pkt(0xA5, 0x00), wait=1.0)
    log(f"    Exit cal: {r.hex(' ') if r else '(none)'}")
    log("")

log("Was there a visible difference between 50 µL and 300 µL?")
note = log_input("Answer: ")
log(f">> {note}")

ser.close()
log("\nDone.")
_log.close()
