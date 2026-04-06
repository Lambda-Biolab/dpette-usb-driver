"""Frame-level encoding / decoding for the dPette serial protocol.

All packets are 6 bytes::

    [HEADER] [CMD] [B2] [B3] [B4] [CHECKSUM]

Header is ``0xFE`` for host→device, ``0xFD`` for device→host.
Checksum is ``sum(bytes[1:5]) & 0xFF``.

This module owns the byte-level framing but knows nothing about
high-level commands like "aspirate" or "dispense".  Actual serial I/O
lives in :mod:`dpette.serial_link`.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

HEADER_TX: int = 0xFE
"""Header byte for host → device packets."""

HEADER_RX: int = 0xFD
"""Header byte for device → host packets."""

PACKET_LEN: int = 6
"""Every packet (TX and RX) is exactly 6 bytes."""


class Command(enum.IntEnum):
    """Known command bytes (confirmed via disassembly + live probing)."""

    HANDSHAKE = 0xA5
    SEND_CALI_VOLUME = 0xA6
    WRITE_EE = 0xA4
    DATA = 0xA3
    ASPIRATE = 0xB3
    DISPENSE = 0xB0


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

    >>> encode_packet(Command.HANDSHAKE).hex(' ')
    'fe a5 00 00 00 a5'
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
# High-level packet builders
# ---------------------------------------------------------------------------


def handshake_packet(param: int = 0) -> bytes:
    """Build a HandShake / StartCalibrate packet.

    ``param=0`` for connection check, ``param=1`` for start calibrate.
    """
    return encode_packet(Command.HANDSHAKE, b2=param)


def send_cali_volume_packet(volume_ul: int) -> bytes:
    """Build a SendCaliVolume packet.

    Volume is encoded as ``volume_µL × 10``, big-endian in bytes[2:3].

    >>> send_cali_volume_packet(1000).hex(' ')
    'fe a6 27 10 00 dd'
    """
    val = volume_ul * 10
    hi = (val >> 8) & 0xFF
    lo = val & 0xFF
    return encode_packet(Command.SEND_CALI_VOLUME, b2=hi, b3=lo)


def read_ee_packet(addr: int) -> bytes:
    """Build a ReadEE packet.

    Address goes in byte[3] (confirmed from PetteCali serial capture).

    >>> read_ee_packet(0x90).hex(' ')
    'fe a3 00 90 00 33'
    """
    return encode_packet(Command.DATA, b2=0x00, b3=addr & 0xFF)


def write_ee_packet(addr: int, value: int = 0) -> bytes:
    """Build a WriteEE packet.

    Address in byte[3], value in byte[4] (confirmed from PetteCali
    serial capture).

    >>> write_ee_packet(0x92, 0x2F).hex(' ')
    'fe a4 00 92 2f 65'
    """
    return encode_packet(Command.WRITE_EE, b2=0x00, b3=addr & 0xFF, b4=value & 0xFF)


def aspirate_packet() -> bytes:
    """Build an Aspirate packet.

    Aspirates at the pipette's current display volume.
    The device returns a double response (started + completed).

    >>> aspirate_packet().hex(' ')
    'fe b3 01 00 00 b4'
    """
    return encode_packet(Command.ASPIRATE, b2=0x01)


def dispense_packet() -> bytes:
    """Build a Dispense packet.

    Dispenses at the pipette's current display volume.

    >>> dispense_packet().hex(' ')
    'fe b0 01 00 00 b1'
    """
    return encode_packet(Command.DISPENSE, b2=0x01)
