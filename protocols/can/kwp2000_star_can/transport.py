"""Transport layer for KWP2000-STAR protocol over CAN bus."""

import time
import logging
from typing import Optional
from protocols.kwp2000 import Transport
from protocols.kwp2000 import TransportException, TimeoutException
from protocols.kwp2000 import TimingParameters, TIMING_PARAMETER_STANDARD
from .constants import TARGET_ADDR, SRC_ADDR


class KWP2000StarTransportCAN(Transport):
    """
    KWP2000-STAR transport layer that wraps a CAN connection.

    Handles STAR frame encoding/decoding (build_frame/parse_frame) and provides
    a Transport interface compatible with KWP2000Client.

    This implementation wraps a CAN connection (e.g., J2534CanConnection)
    and sends/receives STAR frames over CAN bus using rx_id and tx_id.

    Usage:
        from kwp2000_star_can.transport import KWP2000StarTransportCAN
        from kwp2000.client import KWP2000Client
        from j2534.can_connection import J2534CanConnection

        # Create CAN connection
        conn = J2534CanConnection(dll_path='path/to/dll.dll')
        conn.open()

        # Create STAR transport wrapper
        transport = KWP2000StarTransportCAN(can_connection=conn, rx_id=0x612, tx_id=0x6F1)
        client = KWP2000Client(transport)
        with client:
            response = client.startDiagnosticSession(session_type=0x81)
    """

    def __init__(
            self,
            can_connection,
            rx_id: int,
            tx_id: int,
            logger: Optional[logging.Logger] = None
    ):
        """
        Initialize KWP2000-STAR CAN transport.

        Args:
            can_connection: CAN connection object (e.g., J2534CanConnection)
                Must implement: open(), close(), send_can_frame(can_id: int, data: bytes),
                recv_can_frame(timeout: float) -> Optional[Tuple[int, bytes]]
            rx_id: CAN ID to receive frames on
            tx_id: CAN ID to send frames on
            logger: Optional logger instance (default: root logger)
        """
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        # Access timing parameters (used to set wait_frame timeout)
        self.access_timings: TimingParameters = TIMING_PARAMETER_STANDARD

        # Store CAN connection
        self._can_connection = can_connection
        self._rx_id = rx_id
        self._tx_id = tx_id

        self._is_open = False

    def open(self) -> None:
        """Open the transport connection."""
        if self._is_open:
            return

        # Open CAN connection if not already open
        # Check if connection has an '_is_open' attribute (like J2534CanConnection)
        if hasattr(self._can_connection, '_is_open'):
            if not self._can_connection._is_open:
                self._can_connection.open()
        elif hasattr(self._can_connection, 'open'):
            # Try to open, but don't fail if already open
            try:
                self._can_connection.open()
            except (AttributeError, RuntimeError, Exception) as e:
                # Connection might already be open or doesn't support this check
                # Log but continue - the connection will be tested when we use it
                self.logger.debug(f"Could not verify connection state: {e}")

        self._is_open = True
        self.logger.info(f"KWP2000-STAR CAN transport opened (rx_id=0x{self._rx_id:X}, tx_id=0x{self._tx_id:X})")

    def close(self) -> None:
        """Close the transport connection."""
        if not self._is_open:
            return

        try:
            # Don't close the CAN connection as it might be used elsewhere
            # Only mark our transport as closed
            self._is_open = False
            self.logger.info("KWP2000-STAR CAN transport closed")
        except Exception as e:
            self.logger.warning(f"Error closing KWP2000-STAR CAN transport: {e}")

    def send(self, data: bytes) -> None:
        """
        Send KWP2000/UDS payload over BMW-style ISO-TP on CAN.

        The CAN payload uses a 1-byte address (TARGET_ADDR) followed by the
        standard ISO-TP PCI:
        - Single Frame: 0x0L | length in low nibble
        - First Frame:  0x10 | length (12-bit) in next byte
        - Consecutive:  0x2X where X is the sequence counter
        - Flow Control: 0x30 (sent by the tester)

        Args:
            data: Service data bytes (e.g., 0x1A 0x80)

        Raises:
            TransportException: If send fails or transport is not open
        """
        if not self._is_open:
            raise TransportException("Transport not open")

        try:
            payload_len = len(data)

            # Single frame path
            if payload_len <= 7:  # 1 byte address + 1 byte PCI + up to 6 data
                pci = 0x00 | payload_len
                frame = bytes([TARGET_ADDR, pci]) + data
                frame = frame.ljust(8, b"\x00")
                self.logger.debug(f"Sending SF: {frame.hex()}")
                self._can_connection.send_can_frame(self._tx_id, frame)
                return

            # Multi-frame path (First Frame + Consecutive Frames)
            length_high = (payload_len >> 8) & 0x0F
            length_low = payload_len & 0xFF
            first_pci = 0x10 | length_high
            first_frame = bytes([TARGET_ADDR, first_pci, length_low]) + data[:5]
            first_frame = first_frame.ljust(8, b"\x00")
            self.logger.debug(f"Sending FF: {first_frame.hex()}")
            self._can_connection.send_can_frame(self._tx_id, first_frame)

            # For now we always request all remaining frames (block size 0)
            # with minimal separation time (~2 ms).
            self._send_flow_control(block_size=0, separation_time_ms=2)

            seq = 1
            offset = 5
            while offset < payload_len:
                chunk = data[offset:offset + 6]
                pci = 0x20 | (seq & 0x0F)
                frame = bytes([TARGET_ADDR, pci]) + chunk
                frame = frame.ljust(8, b"\x00")
                self.logger.debug(f"Sending CF seq={seq}: {frame.hex()}")
                self._can_connection.send_can_frame(self._tx_id, frame)
                offset += len(chunk)
                seq = (seq + 1) & 0x0F
                if seq == 0:
                    seq = 1  # sequence rolls from 0x0F back to 1
                # Respect separation time
                time.sleep(0.002)

        except Exception as e:
            raise TransportException(f"Failed to send ISO-TP payload: {e}") from e

    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Receive a complete response over BMW-style ISO-TP.

        We expect the ECU to send frames with the first byte equal to SRC_ADDR
        (0xF1 in the captured traffic), followed by ISO-TP PCI and data.

        Args:
            timeout: Ignored; the timeout is derived from access_timings.p2max.

        Returns:
            Complete response payload bytes, or None if no frame arrives before timeout.

        Raises:
            TimeoutException: If a multi-frame response times out mid-stream.
            TransportException: For transport errors or invalid frames.
        """
        del timeout  # unused, timeout derived from access timings

        if not self._is_open:
            raise TransportException("Transport not open")

        try:
            # P2max uses 25 ms resolution, convert to seconds
            calculated_timeout = (self.access_timings.p2max * 25.0) / 1000.0

            buffer = bytearray()
            total_len: Optional[int] = None
            expected_seq = 1

            start_time = time.time()
            last_activity = start_time

            while True:
                now = time.time()
                if now - last_activity >= calculated_timeout:
                    if len(buffer) == 0:
                        return None
                    raise TimeoutException("Timeout waiting for ISO-TP frames")

                remaining = calculated_timeout - (now - last_activity)
                frame_result = self._can_connection.recv_can_frame(timeout=remaining)

                if frame_result is None:
                    if len(buffer) == 0:
                        return None
                    raise TimeoutException("Timeout waiting for ISO-TP frames")

                can_id, can_data = frame_result

                if can_id != self._rx_id:
                    self.logger.debug(f"Ignoring frame with CAN ID 0x{can_id:X} (expected 0x{self._rx_id:X})")
                    continue

                if len(can_data) == 0:
                    self.logger.debug("Ignoring empty CAN frame")
                    continue

                if can_data[0] != SRC_ADDR:
                    self.logger.debug(f"Ignoring frame with unexpected src 0x{can_data[0]:02X}")
                    continue

                # After address, interpret PCI
                if len(can_data) < 2:
                    self.logger.debug("Ignoring too-short CAN frame (missing PCI)")
                    continue

                pci = can_data[1]
                pdu = can_data[2:]

                pci_type = pci & 0xF0
                if pci_type == 0x00:  # Single Frame
                    payload_len = pci & 0x0F
                    buffer.extend(pdu[:payload_len])
                    self.logger.debug(f"Received SF ({payload_len} bytes): {bytes(buffer).hex()}")
                    return bytes(buffer)

                if pci_type == 0x10:  # First Frame
                    total_len = ((pci & 0x0F) << 8) | can_data[2]
                    first_payload = can_data[3:]
                    buffer.extend(first_payload)
                    self.logger.debug(f"Received FF len={total_len}, first chunk {first_payload.hex()}")
                    self._send_flow_control(block_size=0, separation_time_ms=2)
                    expected_seq = 1
                    last_activity = time.time()
                    if len(buffer) >= total_len:
                        return bytes(buffer[:total_len])
                    continue

                if pci_type == 0x20:  # Consecutive Frame
                    seq = pci & 0x0F
                    if seq != expected_seq:
                        raise TransportException(f"Sequence error: expected {expected_seq}, got {seq}")
                    buffer.extend(pdu)
                    self.logger.debug(f"Received CF seq={seq}, chunk {pdu.hex()}")
                    expected_seq = (expected_seq + 1) & 0x0F
                    if expected_seq == 0:
                        expected_seq = 1
                    last_activity = time.time()
                    if total_len is not None and len(buffer) >= total_len:
                        return bytes(buffer[:total_len])
                    continue

                if pci_type == 0x30:  # Flow Control from ECU (unlikely)
                    self.logger.debug("Received FC from ECU, ignoring")
                    last_activity = time.time()
                    continue

                self.logger.debug(f"Unknown PCI type 0x{pci_type:02X}, ignoring frame")
                last_activity = time.time()

        except TimeoutException:
            raise
        except Exception as e:
            raise TransportException(f"Failed to receive ISO-TP payload: {e}") from e

    def _send_flow_control(self, block_size: int, separation_time_ms: int) -> None:
        """Send Flow Control (FC) frame to permit ECU multi-frame responses."""
        fc_pci = 0x30
        frame = bytes([TARGET_ADDR, fc_pci, block_size & 0xFF, separation_time_ms & 0xFF])
        frame = frame.ljust(8, b"\x00")
        self.logger.debug(f"Sending FC: {frame.hex()}")
        self._can_connection.send_can_frame(self._tx_id, frame)

    def set_access_timings(self, timing_parameters: TimingParameters) -> None:
        """
        Set the access timing parameters used for wait_frame timeout calculation.

        This method updates the access_timings variable, which is used to calculate
        the timeout for wait_frame calls. The timeout is calculated from p2max:
        timeout = (p2max * 25.0) / 1000.0 seconds

        Args:
            timing_parameters: TimingParameters instance (e.g., TIMING_PARAMETER_STANDARD or TIMING_PARAMETER_MINIMAL)

        Example:
            from kwp2000.constants import TIMING_PARAMETER_MINIMAL

            transport.set_access_timings(TIMING_PARAMETER_MINIMAL)
        """
        self.access_timings = timing_parameters
        self.logger.info(f"Updated access timing parameters: p2max=0x{timing_parameters.p2max:02X}")

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

