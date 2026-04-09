"""Serial configuration and device discovery for dPette pipettes.

The CP2102 USB-UART bridge (VID 0x10C4, PID 0xEA60) enumerates as
``/dev/ttyUSB*`` on Linux and ``/dev/cu.usbserial-*`` on macOS.
"""

from __future__ import annotations

import glob
import sys
from dataclasses import dataclass

# Confirmed via live hardware probing (2026-04-06).
DEFAULT_BAUDRATE: int = 9600
DEFAULT_READ_TIMEOUT: float = 10.0

CP210X_VID: int = 0x10C4
CP210X_PID: int = 0xEA60


@dataclass(frozen=True)
class SerialConfig:
    """Immutable configuration for a serial connection."""

    port: str
    baudrate: int = DEFAULT_BAUDRATE
    timeout: float = DEFAULT_READ_TIMEOUT
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1


def guess_default_port() -> str | None:
    """Return the first likely CP210x serial port, or ``None``.

    On Linux we look for ``/dev/ttyUSB*``; on macOS for
    ``/dev/cu.usbserial-*`` (Apple Silicon naming) and the legacy
    ``/dev/cu.SLAB_USBtoUART*`` pattern.
    """
    if sys.platform.startswith("linux"):
        candidates = sorted(glob.glob("/dev/ttyUSB*"))
    elif sys.platform == "darwin":
        candidates = sorted(
            glob.glob("/dev/cu.usbserial-*") + glob.glob("/dev/cu.SLAB_USBtoUART*")
        )
    else:
        candidates = []
    return candidates[0] if candidates else None
