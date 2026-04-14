"""High-level driver for DLAB dPette electronic pipettes.

Uses the official DLAB remote control protocol (confirmed EXP-049/050):

    A0 (hello) -> B0 (enter mode) -> B2/B4-B7 (set params) -> B3 (suck/blow)

Supports three operating modes:

- **PI** (Pipetting): aspirate and dispense at a set volume.
- **ST** (Splitting): aspirate once, dispense the same aliquot N times.
- **DI** (Dilution): aspirate/dispense with two different volumes.

If the serial connection fails, the driver degrades gracefully to stub
mode -- all methods log warnings but don't raise, allowing CI/simulation
to run without hardware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpette.logging_utils import get_logger
from dpette.protocol import (
    PACKET_LEN,
    Command,
    KeyAction,
    WorkingMode,
    decode_packet,
    demarcate_packet,
    di1_volume_packet,
    di2_volume_packet,
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
from dpette.safety import DEFAULT_LIMITS, SafetyLimits, validate_speed, validate_volume
from dpette.serial_link import SerialLink

if TYPE_CHECKING:
    from dpette.config import SerialConfig
    from dpette.protocol import Packet

log = get_logger(__name__)

MAX_CONTIGUOUS_CYCLES: int = 50
"""Hard stop: refuse to execute more than this many aspirate/dispense
cycles without an explicit reset.  Prevents mechanical abuse."""

HANDSHAKE_TIMEOUT_S: float = 2.0
READ_TIMEOUT_S: float = 1.0
KEY_TIMEOUT_S: float = 10.0
"""B3 (KEY) commands return 12 bytes; motor travel can take seconds."""


class DPetteDriver:
    """Control interface for a single dPette or dPette+ pipette.

    Supports PI (pipetting), ST (splitting), and DI (dilution) modes
    via the official DLAB remote control protocol.

    If the serial connection fails during ``connect()``, the driver
    enters **stub mode** -- all commands are logged but no serial I/O
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
        self._mode: WorkingMode | None = None

    @property
    def stub_mode(self) -> bool:
        """True if the driver is operating without hardware."""
        return self._stub_mode

    @property
    def mode(self) -> WorkingMode | None:
        """Current operating mode, or None if not yet set."""
        return self._mode

    # -- lifecycle ------------------------------------------------------------

    def connect(self) -> None:
        """Open the serial link and handshake with the device.

        Sends A0 (HELLO). Does NOT auto-enter a working mode -- call
        :meth:`enter_mode` or let :meth:`aspirate`/:meth:`dispense`
        lazily enter PI mode.
        """
        log.info("Connecting to dPette on %s", self._cfg.port)
        try:
            self._link.open()
            resp = self._transact(hello_packet(), timeout=HANDSHAKE_TIMEOUT_S)
            if resp.cmd != Command.HELLO:
                raise RuntimeError(
                    f"Unexpected handshake response cmd 0x{resp.cmd:02X}"
                )
            log.info("Handshake OK (A0)")
            self._connected = True
            self._cycle_count = 0
            # Enter PI mode now so the motor homes before a tip touches liquid
            self.enter_mode(WorkingMode.PI)
        except Exception as exc:
            log.warning("dPette connection failed (%s) -- entering stub mode", exc)
            self._stub_mode = True
            self._connected = True

    def disconnect(self) -> None:
        """Close the serial link."""
        log.info("Disconnecting from dPette")
        if not self._stub_mode:
            self._link.close()
        self._connected = False
        self._mode = None

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Not connected -- call connect() first")

    # -- protocol I/O ---------------------------------------------------------

    def _transact(self, pkt: bytes, timeout: float = READ_TIMEOUT_S) -> Packet:
        """Send *pkt* and return the decoded 6-byte response.

        Flushes any stale bytes in the receive buffer before sending.
        """
        self._link.flush_input()
        self._link.write(pkt)
        raw = self._link.read(PACKET_LEN)
        if len(raw) < PACKET_LEN:
            raise TimeoutError(
                f"Device did not respond within {timeout:.1f}s (got {len(raw)} bytes)"
            )
        return decode_packet(raw)

    def _key_command(self, action: KeyAction) -> Packet:
        """Send B3 (KEY) and read the double 6-byte response.

        The device sends an ACK (b2=0x00) immediately, then a completion
        packet after the motor finishes.  We read them separately so the
        motor has time to complete.  Stale packets from prior commands
        are discarded before sending.

        Returns the second (completion) packet.
        """
        self._link.flush_input()
        # Brief pause to let any late-arriving stale bytes settle
        import time

        time.sleep(0.1)
        self._link.flush_input()
        self._link.write(key_packet(action))
        # Read ACK (arrives quickly)
        ack = self._link.read(PACKET_LEN)
        if len(ack) < PACKET_LEN:
            raise TimeoutError("No ACK response to KEY command")
        # Read completion (may take seconds while motor moves)
        done = self._link.read(PACKET_LEN)
        if len(done) < PACKET_LEN:
            log.warning("KEY command: got ACK but no completion (motor timeout?)")
            return decode_packet(ack)
        return decode_packet(done)

    # -- mode management ------------------------------------------------------

    def enter_mode(self, mode: WorkingMode) -> Packet | None:
        """Enter a working mode via B0 (WOL).

        Triggers motor homing. Must be called before aspirate/dispense
        or mode-specific volume commands.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] enter_mode(%s)", mode.name)
            self._mode = mode
            return None
        log.info("Entering %s mode (B0 param=%d)", mode.name, mode.value)
        resp = self._transact(wol_packet(mode))
        self._mode = mode
        return resp

    def _ensure_pi_mode(self) -> None:
        """Lazily enter PI mode if no mode is set."""
        if self._mode is None:
            self.enter_mode(WorkingMode.PI)

    # -- speed control --------------------------------------------------------

    def set_speed(self, direction: KeyAction, speed: int) -> Packet | None:
        """Set aspirate or dispense speed (B1).

        Parameters
        ----------
        direction:
            ``KeyAction.SUCK`` for aspirate speed, ``KeyAction.BLOW``
            for dispense speed.
        speed:
            Speed level 1-3 (slow to fast).
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] set_speed(%s, %d)", direction.name, speed)
            return None
        validate_speed(speed, self._limits)
        log.info("Setting %s speed to %d", direction.name, speed)
        return self._transact(speed_packet(direction, speed))

    # -- PI mode (pipetting) --------------------------------------------------

    def aspirate(self, volume_ul: float = 0.0) -> Packet | None:
        """Aspirate (draw liquid) via B3 suck.

        If *volume_ul* > 0, sends B2 to set the volume first.
        Auto-enters PI mode if no mode is set.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] aspirate(%.1f uL)", volume_ul)
            return None
        self._check_cycle_limit()
        self._cycle_count += 1
        self._ensure_pi_mode()
        if volume_ul > 0:
            validate_volume(volume_ul, self._limits)
            self.set_volume(volume_ul)
        log.info("Aspirating (cycle %d)", self._cycle_count)
        return self._key_command(KeyAction.SUCK)

    def dispense(self, volume_ul: float = 0.0) -> Packet | None:
        """Dispense (expel liquid) via B3 blow.

        If *volume_ul* > 0, sends B2 to set the volume first.
        Auto-enters PI mode if no mode is set.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] dispense(%.1f uL)", volume_ul)
            return None
        self._check_cycle_limit()
        self._cycle_count += 1
        self._ensure_pi_mode()
        if volume_ul > 0:
            validate_volume(volume_ul, self._limits)
            self.set_volume(volume_ul)
        log.info("Dispensing (cycle %d)", self._cycle_count)
        return self._key_command(KeyAction.BLOW)

    def set_volume(self, volume_ul: float) -> Packet | None:
        """Set the pipetting volume via B2 (PI_VOLUM).

        Controls actual motor travel in PI mode (confirmed EXP-050).
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] set_volume(%.1f uL)", volume_ul)
            return None
        validate_volume(volume_ul, self._limits)
        log.info("Setting PI volume to %.1f uL", volume_ul)
        return self._transact(pi_volume_packet(volume_ul))

    def mix_aspirate(self, volume_ul: float, speed: int = 3) -> Packet:
        """Aspirate step of a mix cycle. Tip should be in liquid.

        Call :meth:`mix_dispense` next, with tip raised above liquid.

        On first call, sets speed and volume. Subsequent calls reuse
        the same settings.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] mix_aspirate(%.1f uL)", volume_ul)
            return None  # type: ignore[return-value]
        self._ensure_pi_mode()
        validate_volume(volume_ul, self._limits)
        self.set_speed(KeyAction.SUCK, speed)
        self.set_speed(KeyAction.BLOW, speed)
        self.set_volume(volume_ul)
        log.info("Mix aspirate %.1f uL", volume_ul)
        return self._key_command(KeyAction.SUCK)

    def mix_dispense(self) -> Packet:
        """Dispense step of a mix cycle. Tip should be above liquid.

        The blow includes a piston return to home, which creates
        suction — if the tip is submerged, this draws extra liquid.
        Always dispense in air or above the liquid surface.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] mix_dispense()")
            return None  # type: ignore[return-value]
        log.info("Mix dispense (blow in air)")
        return self._key_command(KeyAction.BLOW)

    # -- ST mode (splitting) --------------------------------------------------

    def split_setup(self, volume_ul: float, count: int) -> None:
        """Configure splitting: enter ST mode and set volume/count.

        Call this with the tip in air — B0 homes the motor.
        Then call :meth:`split_aspirate` with tip in liquid, and
        :meth:`split_dispense` for each aliquot with tip above liquid.

        Parameters
        ----------
        volume_ul:
            Volume per aliquot (must be <= max_volume / 2).
        count:
            Number of aliquots (volume * count must be <= max_volume).
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] split_setup(%.1f uL x %d)", volume_ul, count)
            return
        validate_volume(volume_ul, self._limits)
        if self._mode != WorkingMode.ST:
            self.enter_mode(WorkingMode.ST)
        log.info("Split setup: %.1f uL x %d aliquots", volume_ul, count)
        self._transact(st_volume_packet(volume_ul))
        self._transact(st_num_packet(count))

    def split_aspirate(self) -> Packet | None:
        """Aspirate the total split volume. Tip should be in liquid."""
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] split_aspirate()")
            return None
        log.info("Split aspirate")
        return self._key_command(KeyAction.SUCK)

    def split_dispense(self) -> Packet | None:
        """Dispense one aliquot. Tip should be above liquid.

        The blow includes a piston return — dispense in air or above
        the liquid surface to avoid drawing extra liquid back in.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] split_dispense()")
            return None
        log.info("Split dispense")
        return self._key_command(KeyAction.BLOW)

    # -- DI mode (dilution) ---------------------------------------------------

    def dilute_setup(self, volume1_ul: float, volume2_ul: float) -> None:
        """Configure dilution: enter DI mode and set both volumes.

        Call this with the tip in air — B0 homes the motor.
        Then use :meth:`dilute_aspirate` (tip in liquid) and
        :meth:`dilute_dispense` (tip above liquid) for each step.

        Parameters
        ----------
        volume1_ul:
            First aspiration volume.
        volume2_ul:
            Second aspiration volume.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] dilute_setup(%.1f, %.1f uL)", volume1_ul, volume2_ul)
            return
        validate_volume(volume1_ul, self._limits)
        validate_volume(volume2_ul, self._limits)
        if self._mode != WorkingMode.DI:
            self.enter_mode(WorkingMode.DI)
        log.info("Dilution setup: vol1=%.1f uL, vol2=%.1f uL", volume1_ul, volume2_ul)
        self._transact(di1_volume_packet(volume1_ul))
        self._transact(di2_volume_packet(volume2_ul))

    def dilute_aspirate(self) -> Packet | None:
        """Aspirate one dilution step. Tip should be in liquid."""
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] dilute_aspirate()")
            return None
        log.info("Dilution aspirate")
        return self._key_command(KeyAction.SUCK)

    def dilute_dispense(self) -> Packet | None:
        """Dispense one dilution step. Tip should be above liquid."""
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] dilute_dispense()")
            return None
        log.info("Dilution dispense")
        return self._key_command(KeyAction.BLOW)

    # -- tip management -------------------------------------------------------

    def eject_tip(self) -> None:
        """Eject the currently attached pipette tip.

        Requires a GPIO-controlled actuator (BSS138 MOSFET or
        optocoupler) wired across the pipette's tip eject button.
        """
        self._require_connected()
        if self._stub_mode:
            log.info("[STUB] eject_tip()")
            return
        raise NotImplementedError(
            "Tip ejection requires GPIO button actuator (BSS138 MOSFET). "
            "See https://github.com/Lambda-Biolab/dpette-usb-driver/issues/3"
        )

    # -- calibration commands (A5/A6, separate from remote control) -----------

    def demarcate(self, param: int = 0) -> Packet | None:
        """Enter or exit calibration mode (A5).

        ``param=0``: exit.  ``param=1``: enter.

        .. warning::
           param=1 causes persistent Err4 on reboot.
        """
        self._require_connected()
        if self._stub_mode:
            return None
        return self._transact(demarcate_packet(param))

    def set_cali_volume(self, volume_ul: int) -> Packet | None:
        """Set calibration display volume (A6). Does NOT control motor."""
        self._require_connected()
        if self._stub_mode:
            return None
        return self._transact(send_cali_volume_packet(volume_ul))

    # -- low-level EEPROM commands --------------------------------------------

    def write_ee(self, addr: int, value: int = 0) -> Packet | None:
        """Write a byte to an EEPROM address (A4)."""
        self._require_connected()
        if self._stub_mode:
            return None
        return self._transact(write_ee_packet(addr, value))

    def read_ee(self, addr: int) -> Packet | None:
        """Read a byte from an EEPROM address (A3)."""
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
                f"Reached {MAX_CONTIGUOUS_CYCLES} contiguous cycles -- "
                "call reset_cycle_count() after inspecting the pipette."
            )
