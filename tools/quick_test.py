#!/usr/bin/env python3
"""A6 persistence test — skip B0 prime to avoid priming artifact.

Enter cal → A6 → exit cal → B3 directly (no B0).
If B3 works after cal exit, compare volumes.
Dial should be at 150.

Logs to captures/live_log.txt
"""

import time

import serial

LOGFILE = "/Users/antoniolamb/repos/dpette-usb-driver/captures/live_log.txt"
_log = open(LOGFILE, "w")  # noqa: SIM115


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


def pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    ck = (cmd + b2 + b3 + b4) & 0xFF
    return bytes([0xFE, cmd, b2, b3, b4, ck])


def sr(p: bytes, wait: float = 0.5) -> bytes:
    ser.reset_input_buffer()
    ser.write(p)
    ser.flush()
    time.sleep(wait)
    return ser.read(64)


log("=== A6 PERSISTENCE — NO B0 PRIME ===")
log("Dial at 150. Enter cal → A6 → exit → B3 directly.")
log("No B0 priming to confuse observation.")
log("")

for vol in [300, 30, 300]:
    log(f"{'=' * 50}")
    log(f"Cal mode A6={vol} → exit → B3 (no B0)")
    log(f"{'=' * 50}")
    log_input("Dismiss Err4 if showing. Press ENTER: ")

    # Handshake
    r = sr(pkt(0xA5), wait=1.0)
    log(f"  Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

    # Enter cal
    r = sr(pkt(0xA5, 0x01), wait=3.0)
    log(f"  Enter cal: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    log_input("  Dismiss Err4, wait for homing. Press ENTER: ")
    time.sleep(5.0)

    # A6 set volume
    val = vol * 10
    r = sr(pkt(0xA6, (val >> 8) & 0xFF, val & 0xFF), wait=0.5)
    log(f"  A6={vol}: ({len(r)}b) {r.hex(' ') if r else '(none)'}")

    # Exit cal
    r = sr(pkt(0xA5, 0x00), wait=1.0)
    log(f"  Exit cal: ({len(r)}b) {r.hex(' ') if r else '(none)'}")
    log_input("  Dismiss Err4. Press ENTER: ")

    # B3 directly — NO B0 prime
    log("  B3 aspirate (NO B0 prime) — tip in water, HANDS OFF")
    log_input("  Press ENTER: ")
    r = sr(pkt(0xB3, 0x01), wait=3.0)
    ok = len(r) >= 12
    log(
        f"  B3: ({len(r)}b) {r.hex(' ') if r else '(none)'}  Motor {'OK' if ok else 'REJECTED'}"
    )

    if ok:
        note = log_input(f"  How much water? (A6={vol}, dial=150): ")
        log(f"  >> {note}")
        log_input("  Dispense (press button or B0). Press ENTER: ")
        sr(pkt(0xB0, 0x01), wait=2.0)
    else:
        log("  B3 rejected — trying with B0 prime...")
        r = sr(pkt(0xB0, 0x01), wait=2.0)
        log_input("  Tip in water. Press ENTER for B3: ")
        r = sr(pkt(0xB3, 0x01), wait=3.0)
        ok = len(r) >= 12
        log(f"  B3 retry: ({len(r)}b)  Motor {'OK' if ok else 'REJECTED'}")
        if ok:
            note = log_input(f"  How much water? (A6={vol}, dial=150): ")
            log(f"  >> {note}")
            log_input("  Dispense. Press ENTER: ")
            sr(pkt(0xB0, 0x01), wait=2.0)
    log("")

log("Did amounts match A6 values (300/30/300) or dial (150)?")
answer = log_input("Answer: ")
log(f">> {answer}")

ser.close()
log("\nDone.")
_log.close()
