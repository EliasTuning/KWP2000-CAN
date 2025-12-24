"""Transport layer for KWP2000-STAR protocol over CAN bus using ISO-TP."""

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
    KWP2000-STAR transport layer that wraps an ISO-TP CAN connection.

    Handles STAR frame encoding/decoding (build_frame/parse_frame) and provides
    a Transport interface compatible with KWP2000Client.

    This implementation wraps an ISO-TP connection (e.g., J2534Connection from udsoncan)
    and sends/receives STAR frames over ISO-TP.

    Usage:
        from kwp2000_star_serial.transport_can import KWP2000StarTransportCAN
        from kwp2000.client import KWP2000Client
        from udsoncan.connections import J2534Connection

        # Create ISO-TP connection
        conn = J2534Connection(windll='path/to/dll', rxid=0x7E8, txid=0x7E0)
        conn.open()

        # Create STAR transport wrapper
        transport = KWP2000StarTransportCAN(conn)
        client = KWP2000Client(transport)
        with client:
            response = client.startDiagnosticSession(session_type=0x81)
    """

    def __init__(
            self,
            isotp_connection,
            logger: Optional[logging.Logger] = None
    ):
        """
        Initialize KWP2000-STAR CAN transport.

        Args:
            isotp_connection: ISO-TP connection object (e.g., J2534Connection from udsoncan)
                Must implement: open(), close(), send(data: bytes), wait_frame(timeout: float) -> Optional[bytes]
            logger: Optional logger instance (default: root logger)
        """
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        # Access timing parameters (used to set wait_frame timeout)
        self.access_timings: TimingParameters = TIMING_PARAMETER_STANDARD

        # Store ISO-TP connection
        self._isotp_connection = isotp_connection

        self._is_open = False

    def open(self) -> None:
        """Open the transport connection."""
        if self._is_open:
            return

        # Open ISO-TP connection if not already open
        # Check if connection has an 'opened' attribute (like J2534Connection)
        if hasattr(self._isotp_connection, 'opened'):
            if not self._isotp_connection.opened:
                self._isotp_connection.open()
        elif hasattr(self._isotp_connection, 'open'):
            # Try to open, but don't fail if already open
            try:
                self._isotp_connection.open()
            except (AttributeError, RuntimeError, Exception) as e:
                # Connection might already be open or doesn't support this check
                # Log but continue - the connection will be tested when we use it
                self.logger.debug(f"Could not verify connection state: {e}")

        self._is_open = True
        self.logger.info("KWP2000-STAR CAN transport opened")

    def close(self) -> None:
        """Close the transport connection."""
        if not self._is_open:
            return

        try:
            # Don't close the ISO-TP connection as it might be used elsewhere
            # Only mark our transport as closed
            self._is_open = False
            self.logger.info("KWP2000-STAR CAN transport closed")
        except Exception as e:
            self.logger.warning(f"Error closing KWP2000-STAR CAN transport: {e}")

    def send(self, data: bytes) -> None:
        """
        Send KWP2000 service data over STAR transport.

        This method wraps the service data (payload) in a STAR frame and sends it
        over the ISO-TP connection.

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

            # Send frame through ISO-TP connection
            self._isotp_connection.send(star_frame)

        except Exception as e:
            raise TransportException(f"Failed to send STAR frame: {e}") from e

    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive a STAR frame, returning the payload.

        This method receives a STAR frame from the ISO-TP connection, parses it,
        and returns the KWP2000 service data (payload).

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

            # Receive STAR frame from ISO-TP connection
            star_frame = self._isotp_connection.wait_frame(timeout=calculated_timeout)

            if star_frame is None:
                return None

            self.logger.debug(f"Received STAR frame: {star_frame.hex()}")

            # Parse STAR frame to extract payload
            try:
                payload, = parse_frame(star_frame)
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

