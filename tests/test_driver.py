"""Placeholder tests for the high-level DPetteDriver API.

These lock in the public interface and confirm that all command methods
raise ``NotImplementedError`` until the protocol is known.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from dpette.config import SerialConfig
from dpette.driver import DPetteDriver, MAX_CONTIGUOUS_CYCLES
from dpette.safety import SafetyError


@pytest.fixture()
def cfg() -> SerialConfig:
    return SerialConfig(port="/dev/ttyUSB0", baudrate=9600)


@pytest.fixture()
def driver(cfg: SerialConfig) -> DPetteDriver:
    return DPetteDriver(cfg)


class TestDriverRequiresConnection:
    """All command methods should fail before connect() is called."""

    def test_identify_requires_connect(self, driver: DPetteDriver) -> None:
        with pytest.raises(RuntimeError, match="Not connected"):
            driver.identify()

    def test_aspirate_requires_connect(self, driver: DPetteDriver) -> None:
        with pytest.raises(RuntimeError, match="Not connected"):
            driver.aspirate()

    def test_dispense_requires_connect(self, driver: DPetteDriver) -> None:
        with pytest.raises(RuntimeError, match="Not connected"):
            driver.dispense()


class TestDriverNotImplemented:
    """Confirm stubs raise NotImplementedError once connected."""

    @patch("dpette.serial_link.serial.Serial")
    def test_identify_not_implemented(
        self, mock_serial_cls: MagicMock, driver: DPetteDriver
    ) -> None:
        mock_serial_cls.return_value = MagicMock(is_open=True)
        driver.connect()
        with pytest.raises(NotImplementedError):
            driver.identify()

    @patch("dpette.serial_link.serial.Serial")
    def test_set_volume_not_implemented(
        self, mock_serial_cls: MagicMock, driver: DPetteDriver
    ) -> None:
        mock_serial_cls.return_value = MagicMock(is_open=True)
        driver.connect()
        with pytest.raises(NotImplementedError):
            driver.set_volume(100.0)

    @patch("dpette.serial_link.serial.Serial")
    def test_aspirate_not_implemented(
        self, mock_serial_cls: MagicMock, driver: DPetteDriver
    ) -> None:
        mock_serial_cls.return_value = MagicMock(is_open=True)
        driver.connect()
        with pytest.raises(NotImplementedError):
            driver.aspirate()


class TestSafetyIntegration:
    """Safety checks should fire before NotImplementedError."""

    @patch("dpette.serial_link.serial.Serial")
    def test_negative_volume_rejected(
        self, mock_serial_cls: MagicMock, driver: DPetteDriver
    ) -> None:
        mock_serial_cls.return_value = MagicMock(is_open=True)
        driver.connect()
        with pytest.raises(SafetyError, match="positive"):
            driver.set_volume(-5.0)

    @patch("dpette.serial_link.serial.Serial")
    def test_excessive_volume_rejected(
        self, mock_serial_cls: MagicMock, driver: DPetteDriver
    ) -> None:
        mock_serial_cls.return_value = MagicMock(is_open=True)
        driver.connect()
        with pytest.raises(SafetyError, match="exceeds maximum"):
            driver.set_volume(99999.0)


class TestCycleLimit:
    @patch("dpette.serial_link.serial.Serial")
    def test_cycle_limit_enforced(
        self, mock_serial_cls: MagicMock, driver: DPetteDriver
    ) -> None:
        mock_serial_cls.return_value = MagicMock(is_open=True)
        driver.connect()
        driver._cycle_count = MAX_CONTIGUOUS_CYCLES
        with pytest.raises(RuntimeError, match="contiguous cycles"):
            driver.aspirate()

    def test_reset_cycle_count(self, driver: DPetteDriver) -> None:
        driver._cycle_count = 42
        driver.reset_cycle_count()
        assert driver._cycle_count == 0
