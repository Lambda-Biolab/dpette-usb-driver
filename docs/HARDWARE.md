---
title: "Hardware notes"
status: "DRAFT"
updated: "2026-04-06"
owner: "lambda biolab"
---

# Hardware notes

## Known models

| Model          | Channels | Volume range  | Notes                |
|----------------|----------|---------------|----------------------|
| dPette         | 1        | TBD           | Single-channel       |
| dPette+ 8-ch   | 8        | TBD           | Eight-channel        |

Both models connect via USB using a Silicon Labs CP210x bridge chip.

## CP210x USB-UART bridge (CONFIRMED)

- **Chip:** CP2102 (confirmed via `system_profiler SPUSBDataType`)
- **VID:** `0x10C4` (Silicon Labs) — **confirmed**
- **PID:** `0xEA60` (CP2102 USB to UART Bridge Controller) — **confirmed**
- **Serial Number:** `0001`
- **Speed:** Up to 12 Mb/s
- **Current Required:** 100 mA
- **Driver:** built into Linux kernel (`cp210x` module); on macOS (Apple
  Silicon), natively supported without extra drivers
- **Enumeration:** `/dev/ttyUSB*` (Linux), `/dev/cu.usbserial-0001` (macOS
  Apple Silicon — NOT `/dev/tty.SLAB_USBtoUART` as older docs suggest)

### Confirming the chip

```bash
# macOS (Apple Silicon) — with pipette plugged in
system_profiler SPUSBDataType | grep -A10 -i "cp210"
ls /dev/cu.usbserial* /dev/tty.usbserial*

# Linux — with pipette plugged in
lsusb | grep -i silicon
# Expected: Bus 00x Device 00y: ID 10c4:ea60 Silicon Labs CP210x ...
lsusb -d 10c4:ea60 -v 2>/dev/null | head -40
dmesg | tail -20 | grep -i cp210
```

## Connecting the pipette

The pipette has two states (confirmed from PetteCali instructions PDF):

1. **Standby state** (not connectable) — screen off or dim.
   Software will get "ReadE TimeOut" or "HandShake TimeOut" in this state.
2. **Connectable state** — press the operation button to wake the device.
   Screen shows volume/mode information.

Connection procedure:

1. Connect the USB cable to the pipette and host PC.
2. Confirm the serial device appears (`/dev/cu.usbserial-0001` on macOS).
3. **Press the operation button** on the pipette to wake it from standby.
4. Software can now connect (HandShake succeeds).

See `captures/static-analysis/page-11.png` and `page-12.png` for photos
of standby vs connectable states.

## Vendor calibration software

- **Name:** PetteCali (downloadable via QR code from DLAB)
- **Platform:** Windows only (XP/Vista/7/8/10 per the dPette+ manual)
- **Architecture:** native C++/Qt6, MinGW x86-64 (NOT .NET as initially assumed)
- **Use for RE:** decompile with Ghidra to extract baud rate, command bytes,
  and packet format; instruction-level disassembly required for byte constants

## Internal MCU

The microcontroller inside the pipette is unknown.  It communicates
with the CP210x bridge over UART.  We do not attempt to identify or
interact with it beyond the serial protocol.
