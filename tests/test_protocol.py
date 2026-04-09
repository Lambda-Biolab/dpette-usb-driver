"""Tests for protocol encoding / decoding.

Uses real packet fixtures captured from live hardware (2026-04-06)
and confirmed against official DLAB protocol (2026-04-09).
"""

from __future__ import annotations

import pytest

from dpette.protocol import (
    HEADER_RX,
    HEADER_TX,
    PACKET_LEN,
    Command,
    KeyAction,
    WorkingMode,
    compute_checksum,
    decode_packet,
    demarcate_packet,
    di1_volume_packet,
    di2_volume_packet,
    encode_packet,
    hello_packet,
    key_packet,
    pi_volume_packet,
    read_ee_packet,
    send_cali_volume_packet,
    speed_packet,
    st_num_packet,
    st_volume_packet,
    wol_packet,
    write_ee_packet,
)

# -- Real packets captured from live hardware --------------------------------

HELLO_TX = bytes.fromhex("fe a0 00 00 00 a0")
HELLO_RX = bytes.fromhex("fd a0 00 00 00 a0")
DEMARCATE_TX = bytes.fromhex("fe a5 00 00 00 a5")
DEMARCATE_RX = bytes.fromhex("fd a5 00 00 00 a5")
CALI_VOL_1000_TX = bytes.fromhex("fe a6 27 10 00 dd")
CALI_VOL_1000_RX = bytes.fromhex("fd a6 00 00 00 a6")
WRITE_EE_RX = bytes.fromhex("fd a4 00 00 00 a4")


class TestComputeChecksum:
    def test_hello(self) -> None:
        assert compute_checksum(0xA0, 0, 0, 0) == 0xA0

    def test_demarcate(self) -> None:
        assert compute_checksum(0xA5, 0, 0, 0) == 0xA5

    def test_cali_volume_1000(self) -> None:
        assert compute_checksum(0xA6, 0x27, 0x10, 0x00) == 0xDD

    def test_wraps_at_8_bits(self) -> None:
        assert compute_checksum(0xFF, 0xFF, 0xFF, 0xFF) == 0xFC


class TestEncodePacket:
    def test_hello(self) -> None:
        assert encode_packet(Command.HELLO) == HELLO_TX

    def test_length_is_always_6(self) -> None:
        assert len(encode_packet(Command.HELLO)) == PACKET_LEN

    def test_header_is_fe(self) -> None:
        pkt = encode_packet(Command.HELLO)
        assert pkt[0] == HEADER_TX

    def test_payload_bytes(self) -> None:
        pkt = encode_packet(0xA6, b2=0x27, b3=0x10)
        assert pkt == CALI_VOL_1000_TX


class TestDecodePacket:
    def test_hello_response(self) -> None:
        pkt = decode_packet(HELLO_RX)
        assert pkt.header == HEADER_RX
        assert pkt.cmd == Command.HELLO
        assert pkt.payload == (0, 0, 0)

    def test_demarcate_response(self) -> None:
        pkt = decode_packet(DEMARCATE_RX)
        assert pkt.cmd == Command.DEMARCATE

    def test_cali_volume_response(self) -> None:
        pkt = decode_packet(CALI_VOL_1000_RX)
        assert pkt.cmd == Command.DMRCT_VOLUM

    def test_write_ee_response(self) -> None:
        pkt = decode_packet(WRITE_EE_RX)
        assert pkt.cmd == Command.EE_WRITE

    def test_raw_roundtrip(self) -> None:
        pkt = decode_packet(HELLO_RX)
        assert pkt.raw == HELLO_RX

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected 6"):
            decode_packet(b"\xfd\xa5\x00")

    def test_wrong_header_raises(self) -> None:
        with pytest.raises(ValueError, match="header"):
            decode_packet(b"\xfe\xa5\x00\x00\x00\xa5")

    def test_bad_checksum_raises(self) -> None:
        with pytest.raises(ValueError, match="Checksum"):
            decode_packet(b"\xfd\xa5\x00\x00\x00\xff")


class TestHelloPacket:
    def test_bytes(self) -> None:
        assert hello_packet() == HELLO_TX

    def test_cmd_byte(self) -> None:
        assert hello_packet()[1] == Command.HELLO


class TestDemarcatePacket:
    def test_exit_cal(self) -> None:
        assert demarcate_packet(0) == DEMARCATE_TX

    def test_enter_cal(self) -> None:
        assert demarcate_packet(1) == bytes.fromhex("fe a5 01 00 00 a6")


class TestSendCaliVolumePacket:
    def test_1000ul(self) -> None:
        assert send_cali_volume_packet(1000) == CALI_VOL_1000_TX

    def test_100ul(self) -> None:
        pkt = send_cali_volume_packet(100)
        assert pkt == bytes.fromhex("fe a6 03 e8 00 91")

    def test_500ul(self) -> None:
        pkt = send_cali_volume_packet(500)
        assert pkt == bytes.fromhex("fe a6 13 88 00 41")


class TestReadEePacket:
    def test_addr_in_b3(self) -> None:
        pkt = read_ee_packet(0x90)
        assert pkt == bytes.fromhex("fe a3 00 90 00 33")

    def test_cmd_is_a3(self) -> None:
        assert read_ee_packet(0x80)[1] == Command.EE_READ

    def test_b2_is_zero(self) -> None:
        assert read_ee_packet(0x82)[2] == 0x00


class TestWriteEePacket:
    def test_addr_in_b3_value_in_b4(self) -> None:
        pkt = write_ee_packet(0x92, value=0x2F)
        assert pkt == bytes.fromhex("fe a4 00 92 2f 65")

    def test_b2_is_zero(self) -> None:
        assert write_ee_packet(0x82, 0x42)[2] == 0x00

    def test_addr_position(self) -> None:
        assert write_ee_packet(0x90, 0x00)[3] == 0x90

    def test_value_position(self) -> None:
        assert write_ee_packet(0x90, 0xAB)[4] == 0xAB


class TestWolPacket:
    def test_pi_mode(self) -> None:
        assert wol_packet(WorkingMode.PI) == bytes.fromhex("fe b0 01 00 00 b1")

    def test_st_mode(self) -> None:
        assert wol_packet(WorkingMode.ST) == bytes.fromhex("fe b0 02 00 00 b2")

    def test_di_mode(self) -> None:
        assert wol_packet(WorkingMode.DI) == bytes.fromhex("fe b0 03 00 00 b3")


class TestSpeedPacket:
    def test_suck_speed_2(self) -> None:
        assert speed_packet(1, 2) == bytes.fromhex("fe b1 01 02 00 b4")

    def test_blow_speed_3(self) -> None:
        assert speed_packet(2, 3) == bytes.fromhex("fe b1 02 03 00 b6")


class TestPiVolumePacket:
    def test_200ul(self) -> None:
        # 200 * 100 = 20000 = 0x004E20
        assert pi_volume_packet(200.0) == bytes.fromhex("fe b2 00 4e 20 20")

    def test_50ul(self) -> None:
        # 50 * 100 = 5000 = 0x001388
        assert pi_volume_packet(50.0) == bytes.fromhex("fe b2 00 13 88 4d")

    def test_1000ul(self) -> None:
        # 1000 * 100 = 100000 = 0x0186A0
        assert pi_volume_packet(1000.0) == bytes.fromhex("fe b2 01 86 a0 d9")


class TestKeyPacket:
    def test_suck(self) -> None:
        assert key_packet(KeyAction.SUCK) == bytes.fromhex("fe b3 01 00 00 b4")

    def test_blow(self) -> None:
        assert key_packet(KeyAction.BLOW) == bytes.fromhex("fe b3 02 00 00 b5")


class TestStVolumePacket:
    def test_100ul(self) -> None:
        # 100 * 100 = 10000 = 0x002710
        assert st_volume_packet(100.0) == bytes.fromhex("fe b4 00 27 10 eb")


class TestStNumPacket:
    def test_5_splits(self) -> None:
        assert st_num_packet(5) == bytes.fromhex("fe b5 05 00 00 ba")


class TestDiVolumePackets:
    def test_di1_200ul(self) -> None:
        assert di1_volume_packet(200.0) == bytes.fromhex("fe b6 00 4e 20 24")

    def test_di2_100ul(self) -> None:
        assert di2_volume_packet(100.0) == bytes.fromhex("fe b7 00 27 10 ee")
