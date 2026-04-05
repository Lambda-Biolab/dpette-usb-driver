"""Frame-level encoding / decoding for the dPette serial protocol.

This module owns the byte-level framing — start bytes, length fields,
checksums, message-type tags — but knows nothing about high-level
commands like "aspirate" or "dispense".

Everything here operates on plain ``bytes`` objects; actual serial I/O
lives in :mod:`dpette.serial_link`.

.. warning::
   Protocol details are not yet known.  Functions raise
   ``NotImplementedError`` until captures are analysed.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from dpette.serial_link import SerialLink


class MessageType(enum.IntEnum):
    """Known message types (to be populated from captures)."""

    PING = 0x01
    IDENTIFY = 0x02
    SET_CAL = 0x03
    ACK = 0x80
    ERROR = 0xFF
    UNKNOWN = 0x00


@dataclass(frozen=True)
class Packet:
    """A single protocol frame."""

    msg_type: MessageType
    payload: bytes
    raw: bytes = b""


def decode_packet(raw: bytes) -> Packet:
    """Decode a raw byte sequence into a structured :class:`Packet`.

    Expected behaviour (once the protocol is known):

    1. Validate a start-of-frame marker or length prefix.
    2. Extract the message-type byte.
    3. Extract the payload (variable length).
    4. Verify the checksum / CRC.
    5. Return a ``Packet`` with all fields populated.

    Raises
    ------
    NotImplementedError
        Always — protocol framing is not yet reverse-engineered.
    ValueError
        (Future) when the raw data fails validation.
    """
    raise NotImplementedError(
        "Protocol framing is not yet reverse-engineered. "
        "Analyse captures in captures/ and update docs/PROTOCOL_NOTES.md first."
    )


def encode_packet(pkt: Packet) -> bytes:
    """Encode a :class:`Packet` into raw bytes suitable for transmission.

    Expected behaviour (once the protocol is known):

    1. Build a frame with start marker, message type, length, payload.
    2. Append checksum / CRC.
    3. Return the complete byte sequence.

    Raises
    ------
    NotImplementedError
        Always — protocol framing is not yet reverse-engineered.
    """
    raise NotImplementedError(
        "Protocol framing is not yet reverse-engineered. "
        "Analyse captures in captures/ and update docs/PROTOCOL_NOTES.md first."
    )


def try_detect_baud(link: SerialLink, candidates: list[int]) -> int:
    """Probe the device at each candidate baud rate and return the first that yields a response.

    Strategy (once a probe packet is known):

    1. For each baud rate in *candidates*, reconfigure the link.
    2. Send a short probe (e.g. a PING packet).
    3. Wait for a non-empty response within the read timeout.
    4. If a response is received, return that baud rate.
    5. If no candidate succeeds, raise ``RuntimeError``.

    Parameters
    ----------
    link:
        An **open** :class:`SerialLink` — the caller owns its lifecycle.
    candidates:
        Baud rates to try, in order.

    Raises
    ------
    NotImplementedError
        Always — we don't yet know which probe byte(s) elicit a response.
    """
    raise NotImplementedError(
        "Cannot detect baud rate until a known probe packet is identified. "
        "Use tools/scan_baud.py with a live device to discover this."
    )
