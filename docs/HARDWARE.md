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
- **Driver:** built into Linux kernel (`cp210x` module); on macOS, may need
  the [Silicon Labs VCP driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
- **Enumeration:** `/dev/ttyUSB*` (Linux), `/dev/cu.SLAB_USBtoUART*` (macOS)

### Confirming the chip

```bash
# Linux — with pipette plugged in
lsusb | grep -i silicon
# Expected: Bus 00x Device 00y: ID 10c4:XXXX Silicon Labs ...

# Detailed descriptor dump
lsusb -d 10c4: -v 2>/dev/null | head -40

# Check kernel module
dmesg | tail -20 | grep -i cp210
```

## Connecting the pipette

The exact procedure to put the pipette into USB communication mode is
not yet documented.  Likely steps (to be verified):

1. Ensure the pipette is powered on (battery charged).
2. Connect the USB cable (type unknown — micro-B or USB-C).
3. The pipette may need to be in a specific menu or mode.
4. The host should see a new `/dev/ttyUSB*` device appear.

**TODO:** document the button sequence or menu navigation required.

## Physical connector

- USB connector type on pipette: **unknown** — inspect and document.
- Cable: standard USB cable (type TBD).

## Internal MCU

The microcontroller inside the pipette is unknown.  It communicates
with the CP210x bridge over UART.  We do not attempt to identify or
interact with it beyond the serial protocol.
