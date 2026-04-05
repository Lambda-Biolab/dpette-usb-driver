"""Smoke tests for SerialLink using a mock serial port."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dpette.config import SerialConfig
from dpette.serial_link import SerialLink


@pytest.fixture()
def cfg() -> SerialConfig:
    return SerialConfig(port="/dev/ttyUSB0", baudrate=9600)


class TestSerialLinkLifecycle:
    def test_not_open_by_default(self, cfg: SerialConfig) -> None:
        link = SerialLink(cfg)
        assert not link.is_open

    @patch("dpette.serial_link.serial.Serial")
    def test_open_close(self, mock_serial_cls: MagicMock, cfg: SerialConfig) -> None:
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_serial_cls.return_value = mock_port

        link = SerialLink(cfg)
        link.open()
        assert link.is_open
        mock_serial_cls.assert_called_once()

        link.close()
        mock_port.close.assert_called_once()
        assert not link.is_open

    @patch("dpette.serial_link.serial.Serial")
    def test_context_manager(self, mock_serial_cls: MagicMock, cfg: SerialConfig) -> None:
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_serial_cls.return_value = mock_port

        with SerialLink(cfg) as link:
            assert link.is_open
        mock_port.close.assert_called_once()


class TestSerialLinkIO:
    def test_write_requires_open(self, cfg: SerialConfig) -> None:
        link = SerialLink(cfg)
        with pytest.raises(RuntimeError, match="not open"):
            link.write(b"\x00")

    def test_read_requires_open(self, cfg: SerialConfig) -> None:
        link = SerialLink(cfg)
        with pytest.raises(RuntimeError, match="not open"):
            link.read(1)

    @patch("dpette.serial_link.serial.Serial")
    def test_write_sends_bytes(self, mock_serial_cls: MagicMock, cfg: SerialConfig) -> None:
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_serial_cls.return_value = mock_port

        link = SerialLink(cfg)
        link.open()
        link.write(b"\x01\x02\x03")
        mock_port.write.assert_called_once_with(b"\x01\x02\x03")

    @patch("dpette.serial_link.serial.Serial")
    def test_read_returns_bytes(self, mock_serial_cls: MagicMock, cfg: SerialConfig) -> None:
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_port.read.return_value = b"\xAA\xBB"
        mock_serial_cls.return_value = mock_port

        link = SerialLink(cfg)
        link.open()
        result = link.read(2)
        assert result == b"\xAA\xBB"
