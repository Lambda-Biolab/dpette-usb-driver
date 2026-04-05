"""Serial configuration and device discovery for dPette pipettes.

The CP210x USB-UART bridge enumerates as /dev/ttyUSB* on Linux and
/dev/cu.SLAB_USBtoUART* on macOS.  Baud rate is unknown until protocol
capture is complete, so we provide a list of candidates to probe.
"""

from __future__ import annotations

import glob
import sys
from dataclasses import dataclass, field


DEFAULT_BAUD_CANDIDATES: list[int] = [9600, 19200, 38400, 57600, 115200]
"""Baud rates to try when auto-detecting the pipette's serial speed."""

DEFAULT_READ_TIMEOUT: float = 1.0
"""Seconds to wait for a serial read before giving up."""


@dataclass(frozen=True)
class SerialConfig:
    """Immutable configuration for a serial connection."""

    port: str
    baudrate: int = 9600
    timeout: float = DEFAULT_READ_TIMEOUT
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1


def guess_default_port() -> str | None:
    """Return the first likely CP210x serial port, or ``None``.

    On Linux we look for ``/dev/ttyUSB*``; on macOS for
    ``/dev/cu.SLAB_USBtoUART*``.  This is a rough heuristic that will
    be refined once we learn the VID/PID of the dPette bridge chip.
    """
    if sys.platform.startswith("linux"):
        candidates = sorted(glob.glob("/dev/ttyUSB*"))
    elif sys.platform == "darwin":
        candidates = sorted(glob.glob("/dev/cu.SLAB_USBtoUART*"))
    else:
        candidates = []
    return candidates[0] if candidates else None
