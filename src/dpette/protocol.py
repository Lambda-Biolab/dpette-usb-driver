"""Frame-level encoding / decoding for the dPette serial protocol.

All packets are 6 bytes::

    [HEADER] [CMD] [B2] [B3] [B4] [CHECKSUM]

Header is ``0xFE`` for host->device, ``0xFD`` for device->host.
Checksum is ``sum(bytes[1:5]) & 0xFF``.

Command names and semantics come from the official DLAB protocol document
(Communication_Protocol_CN.doc, confirmed live in EXP-049/050).

This module owns the byte-level framing but knows nothing about
high-level operations.  Actual serial I/O lives in :mod:`dpette.serial_link`.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

HEADER_TX: int = 0xFE
"""Header byte for host -> device packets."""

HEADER_RX: int = 0xFD
"""Header byte for device -> host packets."""

PACKET_LEN: int = 6
"""Every packet (TX and RX) is exactly 6 bytes."""


class Command(enum.IntEnum):
    """Known command bytes from the official DLAB protocol document.

    Info commands (0xA0-0xA8) handle handshake, EEPROM, and calibration.
    Control commands (0xB0-0xB7) handle remote pipetting, splitting, dilution.
    """

    # -- Info commands --
    HELLO = 0xA0
    INFO = 0xA1
    STA = 0xA2
    EE_READ = 0xA3
    EE_WRITE = 0xA4
    DEMARCATE = 0xA5
    DMRCT_VOLUM = 0xA6
    RESET = 0xA7
    DMRCT_PULSE = 0xA8

    # -- Control commands --
    WOL = 0xB0
    SPEED = 0xB1
    PI_VOLUM = 0xB2
    KEY = 0xB3
    ST_VOLUM = 0xB4
    ST_NUM = 0xB5
    DI1_VOLUM = 0xB6
    DI2_VOLUM = 0xB7


class WorkingMode(enum.IntEnum):
    """Operating modes for the B0 (WOL) command."""

    PI = 1  # Pipetting
    ST = 2  # Splitting
    DI = 3  # Dilution


class KeyAction(enum.IntEnum):
    """Actions for the B3 (KEY) command."""

    SUCK = 1  # Aspirate
    BLOW = 2  # Dispense


@dataclass(frozen=True, slots=True)
class Packet:
    """A single 6-byte protocol frame."""

    header: int
    cmd: int
    b2: int
    b3: int
    b4: int
    checksum: int

    @property
    def payload(self) -> tuple[int, int, int]:
        return (self.b2, self.b3, self.b4)

    @property
    def raw(self) -> bytes:
        return bytes([self.header, self.cmd, self.b2, self.b3, self.b4, self.checksum])


def compute_checksum(cmd: int, b2: int, b3: int, b4: int) -> int:
    """Return ``sum(cmd, b2, b3, b4) & 0xFF``."""
    return (cmd + b2 + b3 + b4) & 0xFF


def encode_packet(cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> bytes:
    """Build a 6-byte TX packet with computed checksum.

    >>> encode_packet(Command.HELLO).hex(' ')
    'fe a0 00 00 00 a0'
    """
    cksum = compute_checksum(cmd, b2, b3, b4)
    return bytes([HEADER_TX, cmd, b2, b3, b4, cksum])


def decode_packet(raw: bytes) -> Packet:
    """Parse a 6-byte response into a :class:`Packet`.

    Raises
    ------
    ValueError
        If *raw* is not 6 bytes, has a wrong header, or fails checksum.
    """
    if len(raw) != PACKET_LEN:
        raise ValueError(f"Expected {PACKET_LEN} bytes, got {len(raw)}")
    header, cmd, b2, b3, b4, cksum = raw
    if header != HEADER_RX:
        raise ValueError(f"Expected RX header 0x{HEADER_RX:02X}, got 0x{header:02X}")
    expected = compute_checksum(cmd, b2, b3, b4)
    if cksum != expected:
        raise ValueError(
            f"Checksum mismatch: got 0x{cksum:02X}, expected 0x{expected:02X}"
        )
    return Packet(header=header, cmd=cmd, b2=b2, b3=b3, b4=b4, checksum=cksum)


# ---------------------------------------------------------------------------
# Volume encoding helpers
# ---------------------------------------------------------------------------


def _encode_volume_x100(volume_ul: float) -> tuple[int, int, int]:
    """Encode volume as 24-bit big-endian (volume * 100).

    Used by B2 (PI_VOLUM), B4 (ST_VOLUM), B6 (DI1_VOLUM), B7 (DI2_VOLUM).
    """
    v = int(volume_ul * 100)
    return ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)


def _encode_volume_x10(volume_ul: int) -> tuple[int, int]:
    """Encode volume as 16-bit big-endian (volume * 10).

    Used by A6 (DMRCT_VOLUM) for calibration.
    """
    v = volume_ul * 10
    return ((v >> 8) & 0xFF, v & 0xFF)


# ---------------------------------------------------------------------------
# Packet builders — Info commands (A0-A8)
# ---------------------------------------------------------------------------


def hello_packet() -> bytes:
    """Build a HELLO handshake packet (A0).

    >>> hello_packet().hex(' ')
    'fe a0 00 00 00 a0'
    """
    return encode_packet(Command.HELLO)


def info_packet() -> bytes:
    """Build an INFO packet (A1) — read device type and volume range."""
    return encode_packet(Command.INFO)


def status_packet() -> bytes:
    """Build a STA packet (A2) — read device status."""
    return encode_packet(Command.STA)


def read_ee_packet(addr: int) -> bytes:
    """Build a ReadEE packet (A3).

    Address goes in byte[3] (confirmed from PetteCali serial capture).

    >>> read_ee_packet(0x90).hex(' ')
    'fe a3 00 90 00 33'
    """
    return encode_packet(Command.EE_READ, b2=0x00, b3=addr & 0xFF)


def write_ee_packet(addr: int, value: int = 0) -> bytes:
    """Build a WriteEE packet (A4).

    Address in byte[3], value in byte[4].

    >>> write_ee_packet(0x92, 0x2F).hex(' ')
    'fe a4 00 92 2f 65'
    """
    return encode_packet(Command.EE_WRITE, b2=0x00, b3=addr & 0xFF, b4=value & 0xFF)


def demarcate_packet(param: int = 0) -> bytes:
    """Build a DEMARCATE packet (A5) — enter/exit calibration mode.

    ``param=0``: exit calibration mode.
    ``param=1``: enter calibration mode.

    .. warning::
       A5 param=1 causes persistent Err4 on reboot. Use with caution.
    """
    return encode_packet(Command.DEMARCATE, b2=param)


def send_cali_volume_packet(volume_ul: int) -> bytes:
    """Build a SendCaliVolume packet (A6).

    Volume is encoded as ``volume_uL * 10``, big-endian in bytes[2:3].
    Only affects display in calibration mode — does NOT control motor.

    >>> send_cali_volume_packet(1000).hex(' ')
    'fe a6 27 10 00 dd'
    """
    hi, lo = _encode_volume_x10(volume_ul)
    return encode_packet(Command.DMRCT_VOLUM, b2=hi, b3=lo)


def reset_packet() -> bytes:
    """Build a RESET packet (A7) — restore factory calibration values."""
    return encode_packet(Command.RESET)


def dmrct_pulse_packet(pulse_count: int) -> bytes:
    """Build a DMRCT_PULSE packet (A8) — set calibration pulse count.

    Pulse count is 16-bit big-endian in bytes[2:3].
    """
    hi = (pulse_count >> 8) & 0xFF
    lo = pulse_count & 0xFF
    return encode_packet(Command.DMRCT_PULSE, b2=hi, b3=lo)


# ---------------------------------------------------------------------------
# Packet builders — Control commands (B0-B7)
# ---------------------------------------------------------------------------


def wol_packet(mode: int) -> bytes:
    """Build a WOL packet (B0) — enter a working mode.

    Mode: 1=PI (pipetting), 2=ST (splitting), 3=DI (dilution).
    Triggers motor homing on the device.

    >>> wol_packet(WorkingMode.PI).hex(' ')
    'fe b0 01 00 00 b1'
    """
    return encode_packet(Command.WOL, b2=mode)


def speed_packet(direction: int, speed: int) -> bytes:
    """Build a SPEED packet (B1) — set aspirate or dispense speed.

    Direction: 1=suck (aspirate), 2=blow (dispense).
    Speed: 1-3 (slow to fast).

    >>> speed_packet(1, 2).hex(' ')
    'fe b1 01 02 00 b4'
    """
    return encode_packet(Command.SPEED, b2=direction, b3=speed)


def pi_volume_packet(volume_ul: float) -> bytes:
    """Build a PI_VOLUM packet (B2) — set pipetting volume.

    Volume is encoded as ``volume_uL * 100``, 24-bit big-endian.
    This controls actual motor travel in PI mode (confirmed EXP-050).

    >>> pi_volume_packet(200.0).hex(' ')
    'fe b2 00 4e 20 20'
    """
    hi, mid, lo = _encode_volume_x100(volume_ul)
    return encode_packet(Command.PI_VOLUM, b2=hi, b3=mid, b4=lo)


def key_packet(action: int) -> bytes:
    """Build a KEY packet (B3) — aspirate or dispense.

    Action: 1=suck (aspirate), 2=blow (dispense).
    Returns double 6-byte response: ACK then completion.

    >>> key_packet(KeyAction.SUCK).hex(' ')
    'fe b3 01 00 00 b4'
    >>> key_packet(KeyAction.BLOW).hex(' ')
    'fe b3 02 00 00 b5'
    """
    return encode_packet(Command.KEY, b2=action)


def st_volume_packet(volume_ul: float) -> bytes:
    """Build a ST_VOLUM packet (B4) — set split volume per aliquot.

    Volume * 100, 24-bit big-endian. Must be <= max_volume / 2.
    """
    hi, mid, lo = _encode_volume_x100(volume_ul)
    return encode_packet(Command.ST_VOLUM, b2=hi, b3=mid, b4=lo)


def st_num_packet(count: int) -> bytes:
    """Build a ST_NUM packet (B5) — set number of splits.

    Single byte count. Constraint: split_volume * count <= max_volume.
    """
    return encode_packet(Command.ST_NUM, b2=count)


def di1_volume_packet(volume_ul: float) -> bytes:
    """Build a DI1_VOLUM packet (B6) — set first dilution volume.

    Volume * 100, 24-bit big-endian.
    """
    hi, mid, lo = _encode_volume_x100(volume_ul)
    return encode_packet(Command.DI1_VOLUM, b2=hi, b3=mid, b4=lo)


def di2_volume_packet(volume_ul: float) -> bytes:
    """Build a DI2_VOLUM packet (B7) — set second dilution volume.

    Volume * 100, 24-bit big-endian.
    """
    hi, mid, lo = _encode_volume_x100(volume_ul)
    return encode_packet(Command.DI2_VOLUM, b2=hi, b3=mid, b4=lo)


# ---------------------------------------------------------------------------
# Backward-compatible aliases (old names -> new names)
# ---------------------------------------------------------------------------

handshake_packet = demarcate_packet
"""Deprecated alias — the old ``handshake_packet()`` actually sent A5
(DEMARCATE), not A0 (HELLO).  Use :func:`hello_packet` for the real
handshake and :func:`demarcate_packet` for calibration mode."""

aspirate_packet = lambda: key_packet(KeyAction.SUCK)  # noqa: E731
"""Deprecated alias — use ``key_packet(KeyAction.SUCK)``."""

dispense_packet = lambda: wol_packet(WorkingMode.PI)  # noqa: E731
"""Deprecated alias — the old ``dispense_packet()`` actually sent B0
(enter PI mode), not B3 blow.  Use ``key_packet(KeyAction.BLOW)`` for
actual dispense."""
