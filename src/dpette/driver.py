"""High-level driver for DLAB dPette electronic pipettes.

Implements the PipetteProtocol interface (connect, disconnect, aspirate,
dispense, eject_tip) for integration with so101-biolab-automation and
PyLabRobot.

If the serial connection fails, the driver degrades gracefully to stub
mode — all methods log warnings but don't raise, allowing CI/simulation
to run without hardware.

Volume control limitations:
    - ``aspirate(volume_ul)`` accepts a volume parameter but the actual
      aspirated volume is determined by the physical dial setting.
    - For true volume control, use calibration mode: ``set_volume()``
      sets the display via A6, then ``trigger_button()`` (GPIO/MOSFET)
      triggers aspiration at that volume.
    - See ``docs/PROTOCOL_NOTES.md`` for the full protocol spec.
"""

from __future__ import annotations

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
    read_ee_packet,
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
    """Control interface for a single dPette or dPette+ pipette.

    Satisfies the ``PipetteProtocol`` structural protocol from
    so101-biolab-automation (connect, disconnect, aspirate, dispense,
    eject_tip).

    If the serial connection fails during ``connect()``, the driver
    enters **stub mode** — all commands are logged but no serial I/O
    occurs.  This allows tests and simulations to run without hardware.
    """

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
        self._stub_mode: bool = False

    @property
    def stub_mode(self) -> bool:
        """True if the driver is operating without hardware."""
        return self._stub_mode

    # -- lifecycle ------------------------------------------------------------

    def connect(self) -> None:
        """Open the serial link, handshake, and prime the device.

        If the connection fails, enters stub mode instead of raising.

        .. note::
           If the pipette shows Err4 on startup, dismiss it with the
           physical button **before** calling this method.
        """
        log.info("Connecting to dPette on %s", self._cfg.port)
        try:
            self._link.open()
            resp = self._transact(handshake_packet(), timeout=HANDSHAKE_TIMEOUT_S)
            if resp.cmd != Command.HANDSHAKE:
                raise RuntimeError(
                    f"Unexpected handshake response cmd 0x{resp.cmd:02X}"
                )
            log.info("Handshake OK — sending B0 prime")
            self._transact(dispense_packet())
            log.info("Prime complete — device ready for aspirate/dispense")
            self._connected = True
            self._cycle_count = 0
        except Exception as exc:
            log.warning("dPette connection failed (%s) — entering stub mode", exc)
            self._stub_mode = True
            self._connected = True  # stub is "connected" for protocol purposes

    def disconnect(self) -> None:
        """Close the serial link."""
        log.info("Disconnecting from dPette")
        if not self._stub_mode:
            self._link.close()
        self._connected = False

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Not connected — call connect() first")

    # -- protocol I/O ---------------------------------------------------------

    def _transact(self, pkt: bytes, timeout: float = READ_TIMEOUT_S) -> Packet:
        """Send *pkt* and return the decoded 6-byte response."""
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

    # -- PipetteProtocol interface --------------------------------------------

    def aspirate(self, volume_ul: float = 0.0) -> Packet | None:
        """Command the pipette to aspirate (draw liquid).

        Parameters
        ----------
        volume_ul:
            Requested volume in microlitres.  **Currently ignored** —
            the actual volume is determined by the physical dial setting.
            For volume control, use :meth:`set_volume` + :meth:`trigger_button`
            in calibration mode.

        Returns the final (completed) packet, or None in stub mode.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] aspirate(%.1f µL)", volume_ul)
            return None
        self._check_cycle_limit()
        self._cycle_count += 1
        if volume_ul > 0:
            validate_volume(volume_ul, self._limits)
        log.info("Aspirating %.1f µL (cycle %d)", volume_ul, self._cycle_count)
        self._link.write(aspirate_packet())
        # Aspirate returns 12 bytes: started (6) + completed (6)
        raw = self._link.read(PACKET_LEN * 2)
        if len(raw) < PACKET_LEN:
            raise TimeoutError("No response to aspirate command")
        final = raw[-PACKET_LEN:]
        return decode_packet(final)

    def dispense(self, volume_ul: float = 0.0) -> Packet | None:
        """Command the pipette to dispense (expel liquid).

        Parameters
        ----------
        volume_ul:
            Requested volume.  **Currently ignored** — dispenses the
            full aspirated amount.

        Returns the response packet, or None in stub mode.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] dispense(%.1f µL)", volume_ul)
            return None
        self._check_cycle_limit()
        self._cycle_count += 1
        log.info("Dispensing %.1f µL (cycle %d)", volume_ul, self._cycle_count)
        return self._transact(dispense_packet())

    def eject_tip(self) -> None:
        """Eject the currently attached pipette tip.

        Requires a GPIO-controlled actuator (BSS138 MOSFET or
        optocoupler) wired across the pipette's tip eject button.
        See GitHub issue #3 for wiring guide.

        Currently raises NotImplementedError — will be implemented
        when the MOSFET button hardware is wired.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] eject_tip()")
            return
        raise NotImplementedError(
            "Tip ejection requires GPIO button actuator (BSS138 MOSFET). "
            "See https://github.com/Lambda-Biolab/dpette-usb-driver/issues/3"
        )

    # -- volume control (calibration mode) ------------------------------------

    def set_volume(self, volume_ul: float) -> Packet | None:
        """Set the target volume via A6 command.

        Only takes effect in calibration mode — the motor will aspirate
        at this volume when the physical button is pressed (or when
        ``trigger_button()`` fires the MOSFET).

        In normal mode, this command has no effect on motor travel.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] set_volume(%.1f µL)", volume_ul)
            return None
        validate_volume(volume_ul, self._limits)
        log.info("Setting calibration volume to %.1f µL", volume_ul)
        return self._transact(send_cali_volume_packet(int(volume_ul)))

    def trigger_button(self) -> None:
        """Electronically press the pipette's physical button.

        Requires a GPIO-controlled actuator (BSS138 MOSFET) wired
        across the button contacts, driven by an RP2040/Arduino GPIO.

        Currently raises NotImplementedError — will be implemented
        when the MOSFET button hardware is wired.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] trigger_button()")
            return
        raise NotImplementedError(
            "Button trigger requires GPIO actuator (BSS138 MOSFET). "
            "See https://github.com/Lambda-Biolab/dpette-usb-driver/issues/3"
        )

    # -- low-level commands ---------------------------------------------------

    def handshake(self, param: int = 0) -> Packet | None:
        """Send a handshake packet and return the response."""
        self._require_connected()
        if self._stub_mode:
            return None
        return self._transact(handshake_packet(param))

    def send_cali_volume(self, volume_ul: int) -> Packet | None:
        """Tell the device which calibration volume to target (in µL)."""
        self._require_connected()
        if self._stub_mode:
            return None
        return self._transact(send_cali_volume_packet(volume_ul))

    def write_ee(self, addr: int, value: int = 0) -> Packet | None:
        """Write a byte to an EEPROM address."""
        self._require_connected()
        if self._stub_mode:
            return None
        return self._transact(write_ee_packet(addr, value))

    def read_ee(self, addr: int) -> Packet | None:
        """Read a byte from an EEPROM address."""
        self._require_connected()
        if self._stub_mode:
            return None
        return self._transact(read_ee_packet(addr))

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
