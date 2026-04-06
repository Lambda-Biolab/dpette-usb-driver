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

## CP210x USB-UART bridge

- **Chip:** CP210x (exact variant unknown — likely CP2102 or CP2104)
- **VID:** `0x10C4` (Silicon Labs) — *to be confirmed*
- **PID:** unknown — *capture `lsusb -v` output when device is connected*
- **Driver:** built into Linux kernel (`cp210x` module); on macOS, natively
  supported — device appears as `/dev/tty.SLAB_USBtoUART` without extra drivers
- **Enumeration:** `/dev/ttyUSB*` (Linux), `/dev/tty.SLAB_USBtoUART` (macOS)

### Confirming the chip

```bash
# macOS — with pipette plugged in
system_profiler SPUSBDataType | grep -A5 -i "silicon\|cp210\|dlab"
ls /dev/tty.*SLAB* /dev/cu.*SLAB*

# Linux — with pipette plugged in
lsusb | grep -i silicon
# Expected: Bus 00x Device 00y: ID 10c4:XXXX Silicon Labs ...
lsusb -d 10c4: -v 2>/dev/null | head -40
dmesg | tail -20 | grep -i cp210
```

### Reading VID/PID from the chip

The `cp210x-program` tool can read the CP210x EEPROM to extract
VID/PID and other configuration: https://github.com/VCTLabs/cp210x-program

## Connecting the pipette

The pipette has two states (confirmed from PetteCali instructions PDF):

1. **Standby state** (not connectable) — screen off or dim.
   Software will get "ReadE TimeOut" or "HandShake TimeOut" in this state.
2. **Connectable state** — press the operation button to wake the device.
   Screen shows volume/mode information.

Connection procedure:

1. Connect the USB cable to the pipette and host PC.
2. Confirm the serial device appears (`/dev/tty.SLAB_USBtoUART` on macOS).
3. **Press the operation button** on the pipette to wake it from standby.
4. Software can now connect (HandShake succeeds).

See `captures/static-analysis/page-11.png` and `page-12.png` for photos
of standby vs connectable states.

## Vendor calibration software

- **Name:** PetteCali (downloadable via QR code from DLAB)
- **Platform:** Windows only (XP/Vista/7/8/10 per the dPette+ manual)
- **Architecture:** almost certainly .NET — decompilable with dnSpyEx or ILSpy
- **Use for RE:** decompile to extract baud rate, command strings, and full
  protocol without any hardware interaction

## Internal MCU

The microcontroller inside the pipette is unknown.  It communicates
with the CP210x bridge over UART.  We do not attempt to identify or
interact with it beyond the serial protocol.
