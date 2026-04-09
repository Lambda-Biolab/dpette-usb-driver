"""Tests for the high-level DPetteDriver API.

Uses mock serial ports -- no hardware needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest

from dpette.config import SerialConfig
from dpette.driver import MAX_CONTIGUOUS_CYCLES, DPetteDriver
from dpette.protocol import Command, KeyAction, WorkingMode
from dpette.safety import SafetyError

# Canned response bytes for mocking
HELLO_RX = bytes.fromhex("fd a0 00 00 00 a0")
WOL_RX = bytes.fromhex("fd b0 00 00 00 b0")
PI_VOLUM_RX = bytes.fromhex("fd b2 00 00 00 b2")
SPEED_RX = bytes.fromhex("fd b1 00 00 00 b1")
KEY_SUCK_ACK = bytes.fromhex("fd b3 00 00 00 b3")
KEY_SUCK_DONE = bytes.fromhex("fd b3 01 00 00 b4")
KEY_BLOW_ACK = bytes.fromhex("fd b3 00 00 00 b3")
KEY_BLOW_DONE = bytes.fromhex("fd b3 02 00 00 b5")
ST_VOLUM_RX = bytes.fromhex("fd b4 00 00 00 b4")
ST_NUM_RX = bytes.fromhex("fd b5 00 00 00 b5")
DI1_VOLUM_RX = bytes.fromhex("fd b6 00 00 00 b6")
DI2_VOLUM_RX = bytes.fromhex("fd b7 00 00 00 b7")
DEMARCATE_RX = bytes.fromhex("fd a5 00 00 00 a5")
CALI_VOL_RX = bytes.fromhex("fd a6 00 00 00 a6")


@pytest.fixture()
def cfg() -> SerialConfig:
    return SerialConfig(port="/dev/ttyUSB0", baudrate=9600)


@pytest.fixture()
def mock_serial() -> Generator[MagicMock, None, None]:
    """Yield a mock serial.Serial that returns HELLO + WOL ACKs for connect."""
    with patch("dpette.serial_link.serial.Serial") as cls:
        port = MagicMock()
        port.is_open = True
        port.in_waiting = 0  # flush_input finds nothing to discard
        port.read.side_effect = [HELLO_RX, WOL_RX]
        cls.return_value = port
        yield port


@pytest.fixture()
def connected_driver(cfg: SerialConfig, mock_serial: MagicMock) -> DPetteDriver:
    """A driver that has already connected via mock (A0 + B0 consumed)."""
    drv = DPetteDriver(cfg)
    drv.connect()
    # Reset side_effect so tests can set their own
    mock_serial.read.side_effect = None
    mock_serial.read.return_value = b""
    return drv


class TestDriverRequiresConnection:
    def test_aspirate_requires_connect(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        with pytest.raises(RuntimeError, match="Not connected"):
            drv.aspirate()

    def test_dispense_requires_connect(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        with pytest.raises(RuntimeError, match="Not connected"):
            drv.dispense()

    def test_eject_tip_requires_connect(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        with pytest.raises(RuntimeError, match="Not connected"):
            drv.eject_tip()


class TestConnect:
    def test_connect_sets_connected(
        self, cfg: SerialConfig, mock_serial: MagicMock
    ) -> None:
        drv = DPetteDriver(cfg)
        drv.connect()
        assert drv._connected

    def test_connect_sends_hello_and_enters_pi(
        self, cfg: SerialConfig, mock_serial: MagicMock
    ) -> None:
        drv = DPetteDriver(cfg)
        drv.connect()
        writes = [call[0][0] for call in mock_serial.write.call_args_list]
        assert len(writes) == 2
        assert writes[0] == bytes.fromhex("fe a0 00 00 00 a0")  # A0 hello
        assert writes[1] == bytes.fromhex("fe b0 01 00 00 b1")  # B0 PI mode
        assert drv.mode == WorkingMode.PI

    def test_connect_stub_mode_on_failure(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError("no port")):
            drv = DPetteDriver(cfg)
            drv.connect()
            assert drv.stub_mode
            assert drv._connected


class TestStubMode:
    def test_stub_aspirate(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            result = drv.aspirate(100.0)
            assert result is None

    def test_stub_dispense(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            result = drv.dispense(100.0)
            assert result is None

    def test_stub_eject_tip(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            drv.eject_tip()

    def test_stub_set_volume(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            result = drv.set_volume(200.0)
            assert result is None

    def test_stub_disconnect(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            drv.disconnect()

    def test_stub_enter_mode(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            drv.enter_mode(WorkingMode.PI)
            assert drv.mode == WorkingMode.PI

    def test_stub_mix(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            drv.mix_aspirate(100.0)
            drv.mix_dispense()

    def test_stub_split(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            drv.split_setup(100.0, count=3)
            drv.split_aspirate()
            drv.split_dispense()

    def test_stub_dilute(self, cfg: SerialConfig) -> None:
        with patch("dpette.serial_link.serial.Serial", side_effect=OSError):
            drv = DPetteDriver(cfg)
            drv.connect()
            drv.dilute_setup(100.0, 200.0)
            drv.dilute_aspirate()
            drv.dilute_dispense()


class TestEnterMode:
    def test_enter_pi_mode(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = WOL_RX
        connected_driver.enter_mode(WorkingMode.PI)
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b0 01 00 00 b1")
        assert connected_driver.mode == WorkingMode.PI

    def test_enter_st_mode(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = WOL_RX
        connected_driver.enter_mode(WorkingMode.ST)
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b0 02 00 00 b2")
        assert connected_driver.mode == WorkingMode.ST

    def test_enter_di_mode(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = WOL_RX
        connected_driver.enter_mode(WorkingMode.DI)
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b0 03 00 00 b3")
        assert connected_driver.mode == WorkingMode.DI


class TestSetSpeed:
    def test_set_suck_speed(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = SPEED_RX
        connected_driver.set_speed(KeyAction.SUCK, 2)
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b1 01 02 00 b4")

    def test_set_blow_speed(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = SPEED_RX
        connected_driver.set_speed(KeyAction.BLOW, 3)
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b1 02 03 00 b6")

    def test_invalid_speed_rejected(self, connected_driver: DPetteDriver) -> None:
        with pytest.raises(SafetyError):
            connected_driver.set_speed(KeyAction.SUCK, 5)


class TestAspirate:
    def test_aspirate_sends_b3_suck(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_SUCK_ACK, KEY_SUCK_DONE]
        connected_driver.aspirate()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 01 00 00 b4")

    def test_aspirate_with_volume_sends_b2(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [PI_VOLUM_RX, KEY_SUCK_ACK, KEY_SUCK_DONE]
        connected_driver.aspirate(200.0)
        writes = [c[0][0] for c in mock_serial.write.call_args_list]
        assert writes[-2] == bytes.fromhex("fe b2 00 4e 20 20")
        assert writes[-1] == bytes.fromhex("fe b3 01 00 00 b4")

    def test_aspirate_returns_completed_packet(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_SUCK_ACK, KEY_SUCK_DONE]
        pkt = connected_driver.aspirate()
        assert pkt is not None
        assert pkt.cmd == Command.KEY
        assert pkt.b2 == 0x01

    def test_aspirate_increments_cycle_count(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_SUCK_ACK, KEY_SUCK_DONE]
        connected_driver.aspirate()
        assert connected_driver._cycle_count == 1


class TestDispense:
    def test_dispense_sends_b3_blow(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_BLOW_ACK, KEY_BLOW_DONE]
        connected_driver.dispense()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 02 00 00 b5")

    def test_dispense_returns_completed_packet(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_BLOW_ACK, KEY_BLOW_DONE]
        pkt = connected_driver.dispense()
        assert pkt is not None
        assert pkt.cmd == Command.KEY
        assert pkt.b2 == 0x02


class TestSetVolume:
    def test_set_volume_sends_b2(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = PI_VOLUM_RX
        pkt = connected_driver.set_volume(200.0)
        assert pkt is not None
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b2 00 4e 20 20")

    def test_negative_volume_rejected(self, connected_driver: DPetteDriver) -> None:
        with pytest.raises(SafetyError, match="positive"):
            connected_driver.set_volume(-5.0)

    def test_excessive_volume_rejected(self, connected_driver: DPetteDriver) -> None:
        with pytest.raises(SafetyError, match="exceeds maximum"):
            connected_driver.set_volume(99999.0)


class TestCalibration:
    def test_demarcate_sends_a5(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = DEMARCATE_RX
        pkt = connected_driver.demarcate(0)
        assert pkt is not None
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe a5 00 00 00 a5")

    def test_set_cali_volume_sends_a6(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = CALI_VOL_RX
        pkt = connected_driver.set_cali_volume(1000)
        assert pkt is not None
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe a6 27 10 00 dd")


class TestSplit:
    def test_split_setup_sends_mode_volume_count(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [WOL_RX, ST_VOLUM_RX, ST_NUM_RX]
        connected_driver.split_setup(100.0, count=3)
        writes = [c[0][0] for c in mock_serial.write.call_args_list]
        assert writes[-3] == bytes.fromhex("fe b0 02 00 00 b2")  # ST mode
        assert writes[-2] == bytes.fromhex("fe b4 00 27 10 eb")  # 100 uL
        assert writes[-1] == bytes.fromhex("fe b5 03 00 00 b8")  # 3 splits

    def test_split_aspirate_sends_suck(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_SUCK_ACK, KEY_SUCK_DONE]
        connected_driver.split_aspirate()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 01 00 00 b4")

    def test_split_dispense_sends_blow(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_BLOW_ACK, KEY_BLOW_DONE]
        connected_driver.split_dispense()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 02 00 00 b5")


class TestDilute:
    def test_dilute_setup_sends_mode_and_volumes(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [WOL_RX, DI1_VOLUM_RX, DI2_VOLUM_RX]
        connected_driver.dilute_setup(200.0, 100.0)
        writes = [c[0][0] for c in mock_serial.write.call_args_list]
        assert writes[-3] == bytes.fromhex("fe b0 03 00 00 b3")  # DI mode
        assert writes[-2] == bytes.fromhex("fe b6 00 4e 20 24")  # 200 uL
        assert writes[-1] == bytes.fromhex("fe b7 00 27 10 ee")  # 100 uL

    def test_dilute_aspirate_sends_suck(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_SUCK_ACK, KEY_SUCK_DONE]
        connected_driver.dilute_aspirate()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 01 00 00 b4")

    def test_dilute_dispense_sends_blow(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_BLOW_ACK, KEY_BLOW_DONE]
        connected_driver.dilute_dispense()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 02 00 00 b5")


class TestMix:
    def test_mix_aspirate_sends_speed_volume_suck(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [
            SPEED_RX,  # B1 suck speed
            SPEED_RX,  # B1 blow speed
            PI_VOLUM_RX,  # B2 volume
            KEY_SUCK_ACK,
            KEY_SUCK_DONE,
        ]
        pkt = connected_driver.mix_aspirate(100.0, speed=3)
        writes = [c[0][0] for c in mock_serial.write.call_args_list]
        assert writes[-1] == bytes.fromhex("fe b3 01 00 00 b4")  # B3 suck
        assert pkt.b2 == 0x01

    def test_mix_dispense_sends_blow(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.side_effect = [KEY_BLOW_ACK, KEY_BLOW_DONE]
        pkt = connected_driver.mix_dispense()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 02 00 00 b5")
        assert pkt.b2 == 0x02


class TestEjectTip:
    def test_eject_tip_raises_not_implemented(
        self, connected_driver: DPetteDriver
    ) -> None:
        with pytest.raises(NotImplementedError, match="BSS138"):
            connected_driver.eject_tip()


class TestCycleLimit:
    def test_cycle_limit_enforced(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        connected_driver._cycle_count = MAX_CONTIGUOUS_CYCLES
        with pytest.raises(RuntimeError, match="contiguous cycles"):
            connected_driver.aspirate()

    def test_reset_cycle_count(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        drv._cycle_count = 42
        drv.reset_cycle_count()
        assert drv._cycle_count == 0
