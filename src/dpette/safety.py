"""Software safety guardrails for pipette operations.

This module validates parameters **before** they reach the serial link.
It never performs I/O itself — it only raises :class:`SafetyError` when
an operation would exceed safe mechanical limits.
"""

from __future__ import annotations

from typing import NamedTuple


class SafetyError(Exception):
    """Raised when a requested operation violates safety limits."""


class SafetyLimits(NamedTuple):
    """Mechanical / operational bounds for a dPette model.

    Values are placeholders until calibrated against real hardware.
    """

    max_volume_ul: float
    """Maximum dispensable volume in microlitres."""

    max_cycles: int
    """Maximum contiguous aspirate/dispense cycles before a forced pause."""

    max_speed_level: int
    """Highest allowed motor speed level (device-specific scale)."""


DEFAULT_LIMITS = SafetyLimits(
    max_volume_ul=1000.0,
    max_cycles=50,
    max_speed_level=3,
)
"""Conservative defaults — speed 1-3 per official DLAB protocol."""


def validate_volume(volume_ul: float, limits: SafetyLimits) -> None:
    """Raise :class:`SafetyError` if *volume_ul* is out of range.

    Parameters
    ----------
    volume_ul:
        Requested volume in microlitres.
    limits:
        Active safety limits for the connected model.
    """
    if volume_ul <= 0:
        raise SafetyError(f"Volume must be positive, got {volume_ul} uL")
    if volume_ul > limits.max_volume_ul:
        raise SafetyError(
            f"Volume {volume_ul} uL exceeds maximum {limits.max_volume_ul} uL"
        )


def validate_speed(speed_level: int, limits: SafetyLimits) -> None:
    """Raise :class:`SafetyError` if *speed_level* is out of range.

    Parameters
    ----------
    speed_level:
        Requested motor speed level.
    limits:
        Active safety limits for the connected model.
    """
    if speed_level < 0:
        raise SafetyError(f"Speed level must be non-negative, got {speed_level}")
    if speed_level > limits.max_speed_level:
        raise SafetyError(
            f"Speed level {speed_level} exceeds maximum {limits.max_speed_level}"
        )
