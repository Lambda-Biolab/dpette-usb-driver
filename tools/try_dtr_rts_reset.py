#!/usr/bin/env python3
"""Try DTR/RTS line manipulation to clear Err4 or enter bootloader.

The CP2102's DTR and RTS lines may be wired to the MCU's reset/boot pins.
Toggling these could trigger a different reset than power cycling.

Run directly:
    python tools/try_dtr_rts_reset.py

Logs to captures/live_log.txt
"""

import time

import serial

LOGFILE = "/Users/antoniolamb/repos/dpette-usb-driver/captures/live_log.txt"
_log = open(LOGFILE, "w")  # noqa: SIM115
PORT = "/dev/cu.usbserial-0001"


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


def pkt(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    ck = (cmd + b2 + b3 + b4) & 0xFF
    return bytes([0xFE, cmd, b2, b3, b4, ck])


def try_handshake(ser: serial.Serial) -> bool:
    ser.reset_input_buffer()
    ser.write(pkt(0xA5))
    ser.flush()
    time.sleep(1)
    r = ser.read(6)
    got = len(r) > 0
    log(
        f"    Handshake: ({len(r)}b) {r.hex(' ') if r else '(none)'}"
        + (" <<<" if got else "")
    )
    return got


def try_bootloader_detect(ser: serial.Serial) -> None:
    """Send common bootloader detection bytes and check for response."""
    # STC ISP sync byte
    ser.reset_input_buffer()
    ser.write(b"\x7f")
    ser.flush()
    time.sleep(0.5)
    r = ser.read(64)
    log(f"    STC sync (0x7F): ({len(r)}b) {r.hex(' ') if r else '(none)'}")

    # STM32 bootloader sync byte
    ser.reset_input_buffer()
    ser.write(b"\x7f")
    ser.flush()
    time.sleep(0.5)
    r = ser.read(64)
    log(f"    STM32 sync (0x7F): ({len(r)}b) {r.hex(' ') if r else '(none)'}")

    # Try reading at different baud (bootloaders often use different baud)
    for baud in [115200, 19200, 4800, 1200]:
        ser.baudrate = baud
        ser.reset_input_buffer()
        ser.write(b"\x7f\x7f\x7f")
        ser.flush()
        time.sleep(0.5)
        r = ser.read(64)
        if r:
            log(f"    Sync @{baud}: ({len(r)}b) {r.hex(' ')} <<<")
    ser.baudrate = 9600


log("=== DTR/RTS LINE MANIPULATION ===")
log("Testing if CP2102 DTR/RTS can reset MCU or enter bootloader.")
log("")

ser = serial.Serial(
    port=PORT,
    baudrate=9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=2.0,
)

# Read current DTR/RTS state
log(f"Initial DTR={ser.dtr}, RTS={ser.rts}")
log("")

# Test 1: Toggle DTR (often wired to MCU reset)
log("=== TEST 1: DTR toggle (possible reset) ===")
log("Setting DTR=False...")
ser.dtr = False
time.sleep(0.5)
log("Setting DTR=True...")
ser.dtr = True
time.sleep(1.0)
log("  Checking if device responds:")
try_handshake(ser)
log_input("  Err4 status? (showing/cleared/changed): ")
log("")

# Test 2: Toggle RTS
log("=== TEST 2: RTS toggle ===")
ser.rts = False
time.sleep(0.5)
ser.rts = True
time.sleep(1.0)
log("  Checking response:")
try_handshake(ser)
log_input("  Err4 status? ")
log("")

# Test 3: DTR+RTS together (Arduino-style reset)
log("=== TEST 3: DTR+RTS together (boot mode entry?) ===")
ser.dtr = False
ser.rts = False
time.sleep(0.2)
ser.dtr = True
ser.rts = True
time.sleep(1.0)
log("  Checking response:")
try_handshake(ser)
try_bootloader_detect(ser)
log_input("  Err4 status? Any display change? ")
log("")

# Test 4: DTR low + RTS high (STM32 boot0=1 + reset)
log("=== TEST 4: DTR=low RTS=high (BOOT0 entry?) ===")
ser.dtr = True  # DTR is inverted on most USB-serial
ser.rts = False
time.sleep(0.2)
ser.dtr = False
ser.rts = True
time.sleep(1.0)
log("  Checking for bootloader:")
try_bootloader_detect(ser)
log_input("  Any display change? ")
log("")

# Test 5: Rapid DTR pulses (some MCUs use pulse count for mode)
log("=== TEST 5: Rapid DTR pulses ===")
for i in range(5):
    ser.dtr = not ser.dtr
    time.sleep(0.1)
ser.dtr = True
time.sleep(1.0)
log("  Checking response:")
try_handshake(ser)
log_input("  Err4 status? ")
log("")

# Test 6: Break condition (some bootloaders trigger on UART break)
log("=== TEST 6: UART break condition ===")
ser.send_break(duration=0.5)
time.sleep(1.0)
log("  Checking response:")
try_handshake(ser)
try_bootloader_detect(ser)
log_input("  Any change? ")

ser.close()
log("\nDone.")
_log.close()
