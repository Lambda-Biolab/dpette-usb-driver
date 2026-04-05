"""Placeholder tests for protocol encoding / decoding.

These assert that the stubs raise ``NotImplementedError`` until the
protocol is reverse-engineered from USB captures.
"""

from __future__ import annotations

import pytest

from dpette.protocol import MessageType, Packet, decode_packet, encode_packet


class TestDecodePacket:
    def test_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="not yet reverse-engineered"):
            decode_packet(b"\x00\x01\x02")


class TestEncodePacket:
    def test_raises_not_implemented(self) -> None:
        pkt = Packet(msg_type=MessageType.PING, payload=b"")
        with pytest.raises(NotImplementedError, match="not yet reverse-engineered"):
            encode_packet(pkt)
