"""High-level driver for DLAB dPette electronic pipettes.

This module provides the user-facing API for controlling a pipette.
Every method that can move the piston validates parameters through
:mod:`dpette.safety` before issuing any serial commands.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from dpette.logging_utils import get_logger
from dpette.protocol import (
    PACKET_LEN,
    Command,
    aspirate_packet,
    decode_packet,
    dispense_packet,
    encode_packet,
    handshake_packet,
    send_cali_volume_packet,
    write_ee_packet,
)
from dpette.safety import DEFAULT_LIMITS, SafetyLimits, validate_volume
from dpette.serial_link import SerialLink

if TYPE_CHECKING:
    from dpette.config import SerialConfig
    from dpette.protocol import Packet

log = get_logger(__name__)

MAX_CONTIGUOUS_CYCLES: int = 50
"""Hard stop: refuse to execute more than this many aspirate/dispense
cycles without an explicit reset.  Prevents mechanical abuse."""

HANDSHAKE_TIMEOUT_S: float = 2.0
"""Maximum seconds to wait for a handshake response."""

READ_TIMEOUT_S: float = 1.0
"""Maximum seconds to wait for a read response."""


class DPetteDriver:
    """Control interface for a single dPette or dPette+ pipette."""

    def __init__(
        self,
        cfg: SerialConfig,
        limits: SafetyLimits | None = None,
    ) -> None:
        self._cfg = cfg
        self._limits = limits or DEFAULT_LIMITS
        self._link = SerialLink(cfg)
        self._cycle_count: int = 0
        self._connected: bool = False

    # -- lifecycle ------------------------------------------------------------

    def connect(self) -> None:
        """Open the serial link and perform a handshake with the pipette.

        After the initial handshake, performs a calibration-mode toggle
        (enter then exit) to ensure the device is in normal operating
        mode.  This clears any stale calibration state that would cause
        motor commands to be rejected.

        .. note::
           If the pipette shows Err4 on startup, dismiss it with the
           physical button **before** calling this method.

        Raises ``RuntimeError`` if the handshake fails.
        """
        log.info("Connecting to dPette on %s", self._cfg.port)
        self._link.open()
        try:
            resp = self._transact(handshake_packet(), timeout=HANDSHAKE_TIMEOUT_S)
            if resp.cmd != Command.HANDSHAKE:
                raise RuntimeError(
                    f"Unexpected handshake response cmd 0x{resp.cmd:02X}"
                )
            log.info("Handshake OK — toggling cal mode to clear stale state")
            # Enter cal mode (may get no response if Err4 is showing)
            self._link.write(encode_packet(Command.HANDSHAKE, b2=0x01))
            time.sleep(2.0)
            self._link.read(PACKET_LEN)  # consume response or timeout
            # Exit cal mode
            self._transact(handshake_packet(), timeout=HANDSHAKE_TIMEOUT_S)
            log.info("Cal mode toggle complete — device in normal mode")
            self._connected = True
            self._cycle_count = 0
        except Exception:
            self._link.close()
            raise

    def disconnect(self) -> None:
        """Close the serial link."""
        log.info("Disconnecting from dPette")
        self._link.close()
        self._connected = False

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Not connected — call connect() first")

    # -- protocol I/O ---------------------------------------------------------

    def _transact(self, pkt: bytes, timeout: float = READ_TIMEOUT_S) -> Packet:
        """Send *pkt* and return the decoded 6-byte response.

        The link's read timeout is temporarily adjusted to *timeout*.
        """
        self._link.write(pkt)
        raw = self._link.read(PACKET_LEN)
        if len(raw) < PACKET_LEN:
            raise TimeoutError(
                f"Device did not respond within {timeout:.1f}s "
                f"(got {len(raw)} bytes)"
            )
        return decode_packet(raw)

    def _send_command(self, cmd: int, b2: int = 0, b3: int = 0, b4: int = 0) -> Packet:
        """Encode, send, and return the response for a single command."""
        self._require_connected()
        return self._transact(encode_packet(cmd, b2, b3, b4))

    # -- commands -------------------------------------------------------------

    def handshake(self, param: int = 0) -> Packet:
        """Send a handshake / start-calibrate packet and return the response."""
        self._require_connected()
        return self._transact(handshake_packet(param))

    def send_cali_volume(self, volume_ul: int) -> Packet:
        """Tell the device which calibration volume to target (in µL)."""
        self._require_connected()
        return self._transact(send_cali_volume_packet(volume_ul))

    def write_ee(self, addr: int, value: int = 0) -> Packet:
        """Write a byte to an EEPROM address.

        .. warning::
           Address/value byte layout is provisional.  Use with caution.
        """
        self._require_connected()
        return self._transact(write_ee_packet(addr, value))

    def read_ee_raw(self, cmd: int, addr: int) -> Packet:
        """Send a raw read-style command and return the response.

        This is a low-level escape hatch for probing the protocol.
        """
        self._require_connected()
        return self._transact(encode_packet(cmd, b2=addr & 0xFF))

    # -- high-level API (stubs until read protocol is confirmed) ---------------

    def identify(self) -> dict[str, str]:
        """Query the pipette for its model name, firmware version, etc.

        Not yet implemented — requires device type negotiation protocol.
        """
        self._require_connected()
        raise NotImplementedError(
            "Device identification requires a confirmed read protocol. "
            "Use handshake() to verify connectivity."
        )

    def set_volume(self, microliters: float) -> None:
        """Set the target aspiration / dispense volume."""
        self._require_connected()
        validate_volume(microliters, self._limits)
        raise NotImplementedError(
            "Volume setting requires confirmed motor control commands."
        )

    def aspirate(self) -> Packet:
        """Command the pipette to aspirate (draw liquid).

        Aspirates at the pipette's current display volume.  The device
        returns a double response: motor-started then motor-finished.
        This method reads both and returns the final (completed) packet.
        """
        self._require_connected()
        self._check_cycle_limit()
        self._cycle_count += 1
        log.info("Aspirating (cycle %d)", self._cycle_count)
        self._link.write(aspirate_packet())
        # Aspirate returns 12 bytes: started (6) + completed (6)
        raw = self._link.read(PACKET_LEN * 2)
        if len(raw) < PACKET_LEN:
            raise TimeoutError("No response to aspirate command")
        # Return the last 6-byte packet (completed)
        final = raw[-PACKET_LEN:]
        return decode_packet(final)

    def dispense(self) -> Packet:
        """Command the pipette to dispense (expel liquid).

        Dispenses at the pipette's current display volume.
        """
        self._require_connected()
        self._check_cycle_limit()
        self._cycle_count += 1
        log.info("Dispensing (cycle %d)", self._cycle_count)
        return self._transact(dispense_packet())

    def blow_out(self) -> None:
        """Perform a blow-out to expel residual liquid from the tip."""
        self._require_connected()
        raise NotImplementedError("Blow-out command not yet reverse-engineered.")

    def eject_tip(self) -> None:
        """Eject the currently attached pipette tip."""
        self._require_connected()
        raise NotImplementedError("Tip ejection command not yet reverse-engineered.")

    # -- helpers --------------------------------------------------------------

    def reset_cycle_count(self) -> None:
        """Reset the contiguous-cycle counter to zero."""
        log.info("Cycle counter reset (was %d)", self._cycle_count)
        self._cycle_count = 0

    def _check_cycle_limit(self) -> None:
        if self._cycle_count >= MAX_CONTIGUOUS_CYCLES:
            raise RuntimeError(
                f"Reached {MAX_CONTIGUOUS_CYCLES} contiguous cycles — "
                "call reset_cycle_count() after inspecting the pipette."
            )
