"""Tests for the high-level DPetteDriver API.

Uses mock serial ports — no hardware needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest

from dpette.config import SerialConfig
from dpette.driver import MAX_CONTIGUOUS_CYCLES, DPetteDriver
from dpette.protocol import Command
from dpette.safety import SafetyError

# Canned response bytes for mocking
HANDSHAKE_RX = bytes.fromhex("fd a5 00 00 00 a5")
CALI_VOL_RX = bytes.fromhex("fd a6 00 00 00 a6")


@pytest.fixture()
def cfg() -> SerialConfig:
    return SerialConfig(port="/dev/ttyUSB0", baudrate=9600)


@pytest.fixture()
def mock_serial() -> Generator[MagicMock, None, None]:
    """Yield a mock serial.Serial that returns handshake ACK by default."""
    with patch("dpette.serial_link.serial.Serial") as cls:
        port = MagicMock()
        port.is_open = True
        port.read.return_value = HANDSHAKE_RX
        cls.return_value = port
        yield port


@pytest.fixture()
def connected_driver(cfg: SerialConfig, mock_serial: MagicMock) -> DPetteDriver:
    """A driver that has already connected via mock."""
    drv = DPetteDriver(cfg)
    drv.connect()
    return drv


class TestDriverRequiresConnection:
    def test_identify_requires_connect(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        with pytest.raises(RuntimeError, match="Not connected"):
            drv.identify()

    def test_aspirate_requires_connect(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        with pytest.raises(RuntimeError, match="Not connected"):
            drv.aspirate()

    def test_handshake_requires_connect(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        with pytest.raises(RuntimeError, match="Not connected"):
            drv.handshake()


class TestConnect:
    def test_connect_sets_connected(
        self, cfg: SerialConfig, mock_serial: MagicMock
    ) -> None:
        drv = DPetteDriver(cfg)
        drv.connect()
        assert drv._connected

    def test_connect_sends_handshake_and_prime(
        self, cfg: SerialConfig, mock_serial: MagicMock
    ) -> None:
        drv = DPetteDriver(cfg)
        drv.connect()
        # Should have written: handshake, then B0 prime
        writes = [call[0][0] for call in mock_serial.write.call_args_list]
        assert len(writes) == 2
        assert writes[0] == bytes.fromhex("fe a5 00 00 00 a5")  # handshake
        assert writes[1] == bytes.fromhex("fe b0 01 00 00 b1")  # B0 prime

    def test_connect_timeout_closes_port(
        self, cfg: SerialConfig, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = b""  # no response
        drv = DPetteDriver(cfg)
        with pytest.raises(TimeoutError):
            drv.connect()
        mock_serial.close.assert_called()


class TestHandshake:
    def test_handshake_returns_packet(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = HANDSHAKE_RX
        pkt = connected_driver.handshake()
        assert pkt.cmd == Command.HANDSHAKE


class TestSendCaliVolume:
    def test_sends_encoded_volume(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = CALI_VOL_RX
        pkt = connected_driver.send_cali_volume(1000)
        assert pkt.cmd == Command.SEND_CALI_VOLUME
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe a6 27 10 00 dd")


ASPIRATE_RX_DOUBLE = bytes.fromhex("fd b3 00 00 00 b3 fd b3 01 00 00 b4")
DISPENSE_RX = bytes.fromhex("fd b0 00 00 00 b0")


class TestAspirate:
    def test_aspirate_sends_b3_01(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = ASPIRATE_RX_DOUBLE
        connected_driver.aspirate()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b3 01 00 00 b4")

    def test_aspirate_returns_completed_packet(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = ASPIRATE_RX_DOUBLE
        pkt = connected_driver.aspirate()
        assert pkt.cmd == Command.ASPIRATE
        assert pkt.b2 == 0x01  # completed

    def test_aspirate_increments_cycle_count(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = ASPIRATE_RX_DOUBLE
        connected_driver.aspirate()
        assert connected_driver._cycle_count == 1


class TestDispense:
    def test_dispense_sends_b0_01(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = DISPENSE_RX
        connected_driver.dispense()
        written = mock_serial.write.call_args[0][0]
        assert written == bytes.fromhex("fe b0 01 00 00 b1")

    def test_dispense_returns_packet(
        self, connected_driver: DPetteDriver, mock_serial: MagicMock
    ) -> None:
        mock_serial.read.return_value = DISPENSE_RX
        pkt = connected_driver.dispense()
        assert pkt.cmd == Command.DISPENSE


class TestSafetyIntegration:
    def test_negative_volume_rejected(self, connected_driver: DPetteDriver) -> None:
        with pytest.raises(SafetyError, match="positive"):
            connected_driver.set_volume(-5.0)

    def test_excessive_volume_rejected(self, connected_driver: DPetteDriver) -> None:
        with pytest.raises(SafetyError, match="exceeds maximum"):
            connected_driver.set_volume(99999.0)


class TestCycleLimit:
    def test_cycle_limit_enforced(self, connected_driver: DPetteDriver) -> None:
        connected_driver._cycle_count = MAX_CONTIGUOUS_CYCLES
        with pytest.raises(RuntimeError, match="contiguous cycles"):
            connected_driver.aspirate()

    def test_reset_cycle_count(self, cfg: SerialConfig) -> None:
        drv = DPetteDriver(cfg)
        drv._cycle_count = 42
        drv.reset_cycle_count()
        assert drv._cycle_count == 0
