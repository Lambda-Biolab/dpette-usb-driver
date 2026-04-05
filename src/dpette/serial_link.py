"""Thin abstraction over pyserial for raw serial I/O.

This module knows nothing about the dPette protocol — it only moves bytes
in and out of a serial port.  Keeping pyserial behind this interface lets
tests swap in a mock or loopback without touching higher layers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import serial

from dpette.logging_utils import get_logger

if TYPE_CHECKING:
    from types import TracebackType

    from dpette.config import SerialConfig

log = get_logger(__name__)


class SerialLink:
    """Manage a single serial connection to the CP210x bridge."""

    def __init__(self, cfg: SerialConfig) -> None:
        self._cfg = cfg
        self._port: serial.Serial | None = None

    # -- lifecycle ------------------------------------------------------------

    def open(self) -> None:
        """Open the serial port described by *cfg*.

        Raises ``serial.SerialException`` if the port cannot be opened.
        """
        if self._port is not None and self._port.is_open:
            log.warning("Port %s already open — skipping", self._cfg.port)
            return
        log.info(
            "Opening %s @ %d baud (timeout=%.1fs)",
            self._cfg.port,
            self._cfg.baudrate,
            self._cfg.timeout,
        )
        self._port = serial.Serial(
            port=self._cfg.port,
            baudrate=self._cfg.baudrate,
            bytesize=self._cfg.bytesize,
            parity=self._cfg.parity,
            stopbits=self._cfg.stopbits,
            timeout=self._cfg.timeout,
        )

    def close(self) -> None:
        """Close the serial port if it is open."""
        if self._port is not None and self._port.is_open:
            log.info("Closing %s", self._cfg.port)
            self._port.close()
        self._port = None

    @property
    def is_open(self) -> bool:
        return self._port is not None and self._port.is_open

    # -- context manager ------------------------------------------------------

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # -- I/O ------------------------------------------------------------------

    def _require_open(self) -> serial.Serial:
        if self._port is None or not self._port.is_open:
            raise RuntimeError("Serial port is not open")
        return self._port

    def write(self, data: bytes) -> None:
        """Write *data* to the serial port.

        All bytes are sent in a single call.  Raises ``RuntimeError`` if
        the port has not been opened.
        """
        port = self._require_open()
        log.debug("TX %d bytes: %s", len(data), data.hex(" "))
        port.write(data)
        port.flush()

    def read(self, n: int) -> bytes:
        """Read up to *n* bytes, returning what arrives within the timeout.

        May return fewer than *n* bytes (including zero) if the timeout
        expires first.
        """
        port = self._require_open()
        data: bytes = port.read(n)
        if data:
            log.debug("RX %d bytes: %s", len(data), data.hex(" "))
        return data

    def read_until(self, terminator: bytes, max_len: int = 4096) -> bytes:
        """Read bytes until *terminator* is seen or *max_len* bytes arrive.

        Returns the accumulated buffer **including** the terminator if found.
        """
        port = self._require_open()
        data: bytes = port.read_until(terminator, max_len)
        if data:
            log.debug("RX %d bytes: %s", len(data), data.hex(" "))
        return data
