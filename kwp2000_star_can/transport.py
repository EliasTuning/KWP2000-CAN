"""Transport layer for KWP2000-STAR protocol over CAN bus."""

import time
import logging
from typing import Optional
from kwp2000.transport import Transport
from kwp2000.exceptions import TransportException, TimeoutException
from kwp2000.constants import TimingParameters, TIMING_PARAMETER_STANDARD
from .frames import build_frame, parse_frame
from .exceptions import InvalidChecksumException, InvalidFrameException


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
        Send KWP2000 service data over STAR transport.

        This method wraps the service data (payload) in a STAR frame and sends it
        over the CAN connection using tx_id.

        Args:
            data: KWP2000 service data bytes (service ID + data, without STAR framing)

        Raises:
            TransportException: If send fails or transport is not open
        """
        if not self._is_open:
            raise TransportException("Transport not open")

        try:
            # Build STAR frame from payload
            star_frame = build_frame(data)
            self.logger.debug(f"Sending STAR frame: {star_frame.hex()}")

            # Send frame through CAN connection using tx_id
            # Split frame into 8-byte CAN frames if needed, padding each to 8 bytes
            frame_offset = 0
            while frame_offset < len(star_frame):
                chunk = star_frame[frame_offset:frame_offset + 8]
                # Pad chunk to exactly 8 bytes with zeros
                padded_chunk = chunk + b'\x00' * (8 - len(chunk))
                self._can_connection.send_can_frame(self._tx_id, padded_chunk)
                frame_offset += 8
                # Add small delay between frames if sending multiple frames
                if frame_offset < len(star_frame):
                    time.sleep(0.001)  # 1ms delay between frames

        except Exception as e:
            raise TransportException(f"Failed to send STAR frame: {e}") from e

    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive a STAR frame, returning the payload.

        This method receives CAN frames from the CAN connection, filters by rx_id,
        reassembles them into a STAR frame, parses it, and returns the KWP2000 service data (payload).

        Args:
            timeout: Maximum time to wait in seconds (ignored, timeout is calculated from access_timings)

        Returns:
            KWP2000 service data bytes (payload), or None if timeout occurs

        Raises:
            TransportException: If receive fails or transport is not open
        """
        if not self._is_open:
            raise TransportException("Transport not open")

        try:
            # Calculate timeout from access_timings.p2max
            # P2max uses 25 ms resolution, convert to seconds
            calculated_timeout = (self.access_timings.p2max * 25.0) / 1000.0

            # Receive CAN frames and filter by rx_id
            star_frame = bytearray()
            start_time = time.time()
            
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= calculated_timeout:
                    if len(star_frame) == 0:
                        return None
                    # If we have partial frame, try to parse it
                    break
                
                # Receive CAN frame
                remaining_timeout = calculated_timeout - elapsed
                frame_result = self._can_connection.recv_can_frame(timeout=remaining_timeout)
                
                if frame_result is None:
                    # Timeout - if we have partial frame, try to parse it
                    if len(star_frame) > 0:
                        break
                    return None
                
                can_id, can_data = frame_result
                
                # Filter by rx_id
                if can_id != self._rx_id:
                    self.logger.debug(f"Ignoring frame with CAN ID 0x{can_id:X} (expected 0x{self._rx_id:X})")
                    continue
                
                # Append data to frame
                star_frame.extend(can_data)
                
                # Check if we have a complete frame
                # STAR frame format: [SRC_ADDR, length, payload...]
                # Minimum frame size is 2 bytes (SRC_ADDR + length)
                if len(star_frame) >= 2:
                    expected_length = 2 + star_frame[1]  # SRC_ADDR + length + payload
                    if len(star_frame) >= expected_length:
                        # We have a complete frame
                        break

            if len(star_frame) == 0:
                return None

            self.logger.debug(f"Received STAR frame: {bytes(star_frame).hex()}")

            # Parse STAR frame to extract payload
            try:
                payload, = parse_frame(bytes(star_frame))
                self.logger.debug(f"Parsed payload: {payload.hex()}")
                return payload
            except (InvalidFrameException, InvalidChecksumException) as e:
                raise TransportException(f"Failed to parse STAR frame: {e}") from e

        except TransportException:
            raise  # Re-raise transport exceptions
        except Exception as e:
            raise TransportException(f"Failed to receive STAR frame: {e}") from e

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

