# dPette Button MOSFET Mod — Hardware Guide

This document covers the hardware modification required for fully automated,
volume-controlled pipetting. The mod wires a BSS138 MOSFET across the pipette's
physical button contacts, allowing any microcontroller GPIO pin to simulate a
button press electronically.

## Why this is needed

The dPette's volume control (A6 command) only takes effect when the physical
button is pressed — there is no serial command that triggers aspiration at the
A6-set volume. After 48 experiments exhausting the full serial protocol surface,
a hardware button actuator is the confirmed path to full automation.

See [`EXPERIMENT_LOG.md`](EXPERIMENT_LOG.md) for the complete investigation.

---

## Bill of Materials

### Single Reichelt.de order (~€20.75 + shipping)

All items are in stock with 1–2 business day delivery.

| Product# | Description | Price | Purpose |
|----------|-------------|-------|---------|
| `RASP PI PICO 2` | Raspberry Pi Pico 2, RP235x, Cortex-M33, microUSB | €4.90 | GPIO controller |
| `DEBO LOGIC 4CH` | Bidirectional logic level converter, 4-channel (BSS138) | €5.30 | MOSFET button switch |
| `DEBO KABELSET8` | Jumper cable set, 20cm, 3×40 cables (M-M, F-F, F-M) | €4.50 | Wiring |
| `DELOCK 66694` | Pin header, 40-pin, 2.54mm pitch, straight, 5-pack | €1.85 | Pico header |
| `BREADBOARD1 400` | Breadboard, 400 contacts, transparent | €2.70 | Prototyping |
| `LOGILINK CU0007B` | USB 2.0 cable, USB-A to Micro-B, 2m | €1.50 | Pico power/programming |

**Total: ~€20.75** (most items are reusable lab infrastructure)

> The actual per-pipette cost of the mod is **€5.30** (one DEBO LOGIC 4CH board).
> The Pico, breadboard, and wires are shared infrastructure reused across pipettes.

### You also need (from your lab)

- Soldering iron + solder + flux
- Multimeter (continuity mode)
- Small Phillips screwdriver
- A computer with Python (to program the Pico and run the driver)

---

## Circuit

The DEBO LOGIC 4CH board exposes 4× BSS138 MOSFETs on 2.54mm headers.
Use one channel (e.g. channel 1):

```
Pico GP15 ──── LV1 pin (board)
Pico 3V3  ──── LV  pin (board)
Pico GND  ──── GND pin (LV side)

TX1 pin (board) ──── Button pad A (pipette PCB)
GND pin (HV side)──── Button pad B (pipette PCB)
```

When `GP15` goes HIGH: MOSFET conducts → pads A/B shorted → MCU sees button press.  
When `GP15` goes LOW: MOSFET off → button open → normal state.

No additional resistors needed — the DEBO LOGIC 4CH board has pull-ups built in.

---

## Step-by-Step Instructions

### Phase A — Set up the Pico

**1. Solder pin headers**  
Place the 40-pin header strip into the breadboard (to hold it straight), rest
the Pico on top, solder all 40 pins. ~10 minutes.

**2. Flash MicroPython firmware**  
- Hold `BOOTSEL` while plugging in the micro-USB cable → mounts as `RPI-RP2`
- Download MicroPython `.uf2` from https://micropython.org/download/RPI_PICO2
- Drag the `.uf2` onto the `RPI-RP2` drive → Pico reboots automatically

**3. Verify in REPL**  
Open a serial terminal (Thonny, or `screen /dev/tty.usbmodem* 115200`).
Type `print("ok")` at the `>>>` prompt to confirm firmware is running.

---

### Phase B — Wire the level shifter

**4. Insert DEBO LOGIC 4CH into breadboard**

**5. Connect Pico → level shifter**

| Pico pin | Board pin | Notes |
|----------|-----------|-------|
| `3V3 OUT` (pin 36) | `LV` | Logic supply |
| `GND` (pin 38) | `GND` (LV side) | Ground |
| `GP15` (pin 20) | `LV1` | Control signal |

Leave `TX1` and HV-side `GND` unconnected until Phase C.

---

### Phase C — Open the pipette and wire the button

**6. Open the pipette**  
Unscrew the body (2–4 Phillips screws on the back/side panel). Work slowly —
case halves may have snap clips.

**7. Locate the tactile button**  
Find the push button PCB component (typically 6×6mm or 3×6mm square).

**8. Identify the two active pads**  
Set multimeter to continuity mode. Probe the button pads while pressing it —
beeps when you find the two pads that complete the circuit.

**9. Solder two short wires (~5cm) to the button pads**  
- Apply flux to each pad
- Tin the pad, tack one wire per pad
- Verify no solder bridges to adjacent components

**10. Route wires out of the pipette**  
Thread wires through a gap in the case seam or a 2mm drilled hole. Close the case.

**11. Connect button wires to level shifter**

| Wire | Board pin |
|------|-----------|
| Button pad A | `TX1` (HV side) |
| Button pad B | `GND` (HV side) |

---

### Phase D — Test

**12. Quick MicroPython test**

```python
from machine import Pin
import time

button = Pin(15, Pin.OUT)
button.value(1)    # MOSFET ON → button "pressed"
time.sleep(0.1)
button.value(0)    # MOSFET OFF → button released
```

With the pipette in calibration mode and A6 set, this should trigger
aspiration. You should hear the motor.

**13. Full automation cycle test**

```python
# Enter cal mode via MOSFET button press (NOT serial A5 b2=1 — causes Err4)
trigger_button()            # enters cal mode

set_volume(200)             # A6 serial command
trigger_button()            # aspirates 200 µL
dispense()                  # B0 serial command

set_volume(50)              # A6 serial command
trigger_button()            # aspirates 50 µL
dispense()                  # B0 serial command
```

See `examples/volume_control.py` for the complete integration.

---

## Important: Avoiding Err4

> **Do NOT send `FE A5 01` (serial cal mode entry) on a fresh device.**
>
> Err4 was triggered specifically by the serial `A5 b2=1` command — NOT by
> pressing the physical button. Always enter calibration mode by pressing the
> button (via MOSFET), never via the serial command. This avoids the persistent
> Err4 flag entirely.
>
> If Err4 appears, it can be dismissed with a physical button press and the
> device functions normally. It does not affect serial UART communication after
> dismissal.

---

## Cost in context

| Solution | Total cost | Disposable tips | Serial volume control |
|----------|------------|-----------------|----------------------|
| **dPette + this mod** | **~$150** | **Yes** | **Yes (A6 + MOSFET)** |
| INTEGRA VIAFLO + ASSIST stand | ~$4,000+ | Yes | Partial |
| Opentrons OT-2 (full robot) | ~$10,000+ | Yes | Full API |
| ac-rad Digital Pipette v2 | ~$200 | No (syringe) | Arduino |

The dPette + MOSFET mod is the only open-source, disposable-tip,
API-controlled pipette under $200.
