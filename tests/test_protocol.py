"""Tests for protocol encoding / decoding.

Uses real packet fixtures captured from live hardware (2026-04-06).
"""

from __future__ import annotations

import pytest

from dpette.protocol import (
    HEADER_RX,
    HEADER_TX,
    PACKET_LEN,
    Command,
    aspirate_packet,
    compute_checksum,
    decode_packet,
    dispense_packet,
    encode_packet,
    handshake_packet,
    read_ee_packet,
    send_cali_volume_packet,
    write_ee_packet,
)

# -- Real packets captured from live hardware --------------------------------

HANDSHAKE_TX = bytes.fromhex("fe a5 00 00 00 a5")
HANDSHAKE_RX = bytes.fromhex("fd a5 00 00 00 a5")
CALI_VOL_1000_TX = bytes.fromhex("fe a6 27 10 00 dd")
CALI_VOL_1000_RX = bytes.fromhex("fd a6 00 00 00 a6")
WRITE_EE_RX = bytes.fromhex("fd a4 00 00 00 a4")


class TestComputeChecksum:
    def test_handshake(self) -> None:
        assert compute_checksum(0xA5, 0, 0, 0) == 0xA5

    def test_cali_volume_1000(self) -> None:
        # 1000 µL × 10 = 10000 = 0x2710
        assert compute_checksum(0xA6, 0x27, 0x10, 0x00) == 0xDD

    def test_wraps_at_8_bits(self) -> None:
        assert compute_checksum(0xFF, 0xFF, 0xFF, 0xFF) == 0xFC


class TestEncodePacket:
    def test_handshake(self) -> None:
        assert encode_packet(Command.HANDSHAKE) == HANDSHAKE_TX

    def test_length_is_always_6(self) -> None:
        assert len(encode_packet(Command.HANDSHAKE)) == PACKET_LEN

    def test_header_is_fe(self) -> None:
        pkt = encode_packet(Command.HANDSHAKE)
        assert pkt[0] == HEADER_TX

    def test_payload_bytes(self) -> None:
        pkt = encode_packet(0xA6, b2=0x27, b3=0x10)
        assert pkt == CALI_VOL_1000_TX


class TestDecodePacket:
    def test_handshake_response(self) -> None:
        pkt = decode_packet(HANDSHAKE_RX)
        assert pkt.header == HEADER_RX
        assert pkt.cmd == Command.HANDSHAKE
        assert pkt.payload == (0, 0, 0)

    def test_cali_volume_response(self) -> None:
        pkt = decode_packet(CALI_VOL_1000_RX)
        assert pkt.cmd == Command.SEND_CALI_VOLUME
        assert pkt.b2 == 0
        assert pkt.b3 == 0
        assert pkt.b4 == 0

    def test_write_ee_response(self) -> None:
        pkt = decode_packet(WRITE_EE_RX)
        assert pkt.cmd == Command.WRITE_EE

    def test_raw_roundtrip(self) -> None:
        pkt = decode_packet(HANDSHAKE_RX)
        assert pkt.raw == HANDSHAKE_RX

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected 6"):
            decode_packet(b"\xfd\xa5\x00")

    def test_wrong_header_raises(self) -> None:
        with pytest.raises(ValueError, match="header"):
            decode_packet(b"\xfe\xa5\x00\x00\x00\xa5")

    def test_bad_checksum_raises(self) -> None:
        with pytest.raises(ValueError, match="Checksum"):
            decode_packet(b"\xfd\xa5\x00\x00\x00\xff")


class TestHandshakePacket:
    def test_default_param(self) -> None:
        assert handshake_packet() == HANDSHAKE_TX

    def test_start_calibrate(self) -> None:
        pkt = handshake_packet(param=1)
        assert pkt == bytes.fromhex("fe a5 01 00 00 a6")


class TestSendCaliVolumePacket:
    def test_1000ul(self) -> None:
        assert send_cali_volume_packet(1000) == CALI_VOL_1000_TX

    def test_100ul(self) -> None:
        # 100 × 10 = 1000 = 0x03E8
        pkt = send_cali_volume_packet(100)
        assert pkt == bytes.fromhex("fe a6 03 e8 00 91")

    def test_500ul(self) -> None:
        # 500 × 10 = 5000 = 0x1388
        pkt = send_cali_volume_packet(500)
        assert pkt == bytes.fromhex("fe a6 13 88 00 41")


class TestReadEePacket:
    def test_addr_in_b3(self) -> None:
        """Address goes in byte[3] — confirmed from PetteCali capture."""
        pkt = read_ee_packet(0x90)
        assert pkt == bytes.fromhex("fe a3 00 90 00 33")

    def test_cmd_is_a3(self) -> None:
        assert read_ee_packet(0x80)[1] == Command.DATA

    def test_b2_is_zero(self) -> None:
        assert read_ee_packet(0x82)[2] == 0x00


class TestWriteEePacket:
    def test_addr_in_b3_value_in_b4(self) -> None:
        """Address in byte[3], value in byte[4] — from PetteCali capture."""
        pkt = write_ee_packet(0x92, value=0x2F)
        assert pkt == bytes.fromhex("fe a4 00 92 2f 65")

    def test_b2_is_zero(self) -> None:
        assert write_ee_packet(0x82, 0x42)[2] == 0x00

    def test_addr_position(self) -> None:
        assert write_ee_packet(0x90, 0x00)[3] == 0x90

    def test_value_position(self) -> None:
        assert write_ee_packet(0x90, 0xAB)[4] == 0xAB


class TestAspiratePacket:
    def test_bytes(self) -> None:
        assert aspirate_packet() == bytes.fromhex("fe b3 01 00 00 b4")

    def test_cmd_byte(self) -> None:
        assert aspirate_packet()[1] == Command.ASPIRATE

    def test_b2_is_trigger(self) -> None:
        assert aspirate_packet()[2] == 0x01


class TestDispensePacket:
    def test_bytes(self) -> None:
        assert dispense_packet() == bytes.fromhex("fe b0 01 00 00 b1")

    def test_cmd_byte(self) -> None:
        assert dispense_packet()[1] == Command.DISPENSE

    def test_b2_is_trigger(self) -> None:
        assert dispense_packet()[2] == 0x01
