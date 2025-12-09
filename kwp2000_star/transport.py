"""Transport layer for KWP2000-STAR protocol over COM port."""

import time
import logging
from typing import Optional, List
from kwp2000.transport import Transport
from kwp2000.exceptions import TransportException, TimeoutException, NegativeResponseException
from kwp2000.constants import TimingParameters, TIMING_PARAMETER_STANDARD
from kwp2000_star.frames import build_frame, parse_frame
from kwp2000_star.exceptions import InvalidChecksumException, InvalidFrameException
from comport import ComportTransport

try:
    import serial
except ImportError:
    raise ImportError(
        "pyserial is required for KWP2000-STAR transport. "
        "Install it with: pip install pyserial"
    )


class KWP2000StarTransport(Transport):
    """
    KWP2000-STAR transport layer that wraps a COM port transport.
    
    Handles STAR frame encoding/decoding (build_frame/parse_frame) and provides
    a Transport interface compatible with KWP2000Client.
    
    This implementation is synchronous and does not use threading.
    
    Usage:
        from kwp2000_star.transport import KWP2000StarTransport
        from kwp2000.client import KWP2000Client
        
        transport = KWP2000StarTransport(port='COM1', baudrate=9600)
        client = KWP2000Client(transport)
        with client:
            response = client.startDiagnosticSession(session_type=0x81)
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
        bytesize: int = serial.EIGHTBITS,
        parity: str = serial.PARITY_EVEN,
        stopbits: float = serial.STOPBITS_TWO,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize KWP2000-STAR transport.
        
        Args:
            port: COM port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Baud rate (default: 9600)
            timeout: Default timeout in seconds for read operations
            bytesize: Number of data bits (default: 8)
            parity: Parity setting (default: NONE)
            stopbits: Number of stop bits (default: 1)
            logger: Optional logger instance (default: root logger)
        """
        self.logger = logger if logger is not None else logging.getLogger(__name__)
        
        # Access timing parameters (used to set wait_frame timeout)
        self.access_timings: TimingParameters = TIMING_PARAMETER_STANDARD
        
        # Create underlying COM port transport
        self._comport_transport = ComportTransport(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            logger=self.logger
        )
        
        self._is_open = False
    
    def open(self) -> None:
        """Open the transport connection."""
        if self._is_open:
            return
        
        self._comport_transport.open()
        self._is_open = True
        self.logger.info("KWP2000-STAR transport opened")
    
    def close(self) -> None:
        """Close the transport connection."""
        if not self._is_open:
            return
        
        try:
            self._comport_transport.close()
            self._is_open = False
            self.logger.info("KWP2000-STAR transport closed")
        except Exception as e:
            self.logger.warning(f"Error closing KWP2000-STAR transport: {e}")
    
    def send(self, data: bytes) -> None:
        """
        Send KWP2000 service data over STAR transport.
        
        This method wraps the service data (payload) in a STAR frame and sends it.
        
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

            
            # Send frame through COM port transport
            self._comport_transport.send(star_frame)
            
        except Exception as e:
            raise TransportException(f"Failed to send STAR frame: {e}") from e
    
    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive a STAR frame, returning the payload.
        
        This method receives a STAR frame from the COM port, parses it, and returns
        the KWP2000 service data (payload).
        
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
            
            # Receive STAR frame from COM port transport
            star_frame = self._comport_transport.wait_frame(timeout=calculated_timeout)
            
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
    
    def set_baudrate(self, baudrate: int) -> None:
        """
        Change the baudrate of the underlying COM port connection.
        
        This method can be called while the transport is open to dynamically change
        the baudrate. The transport connection must be open.
        
        Args:
            baudrate: New baudrate value
            
        Raises:
            TransportException: If transport is not open or baudrate change fails
        """
        if not self._is_open:
            raise TransportException("Transport not open")
        
        self._comport_transport.set_baudrate(baudrate)
        self.logger.info(f"Changed KWP2000-STAR transport baudrate to {baudrate}")
    
    def identify_baudrate(
        self,
        client,
        baudrates: Optional[List[int]] = None,
        timeout: float = 0.1,
        verbose: bool = False
    ) -> Optional[int]:
        """
        Identify the working baudrate by scanning through available baudrates.
        
        This method loops through available KWP2000 baudrates, sends TesterPresent
        messages at each baudrate, and returns the first baudrate that receives a response.
        
        Args:
            client: KWP2000Client instance to use for sending TesterPresent messages
            baudrates: List of baudrates to test (default: common KWP2000 baudrates)
            timeout: Timeout in seconds for each TesterPresent request (default: 0.1 = 100ms)
            verbose: If True, print progress messages (default: False)
            
        Returns:
            First working baudrate found, or None if no baudrate responds
            
        Raises:
            TransportException: If transport is not open
        """
        if not self._is_open:
            raise TransportException("Transport not open")
        
        # Default baudrates to test (in order of common usage)
        if baudrates is None:
            baudrates = [
                10400,   # 10.4 kbps (common for older ECUs)
                9600,    # 9.6 kbps (very common)
                19200,   # 19.2 kbps
                20800,   # 20.8 kbps
                38400,   # 38.4 kbps
                57600,   # 57.6 kbps
                115200,  # 115.2 kbps
                125000,  # 125 kbps (high speed)
            ]
        
        if verbose:
            self.logger.info(f"Starting baudrate identification, testing {len(baudrates)} baudrates...")
        
        # Store original baudrate to restore later if no working baudrate is found
        original_baudrate = self._comport_transport._serial.baudrate
        found_baudrate = None
        
        try:
            for baudrate in baudrates:
                try:
                    if verbose:
                        self.logger.info(f"Testing {baudrate} baud...")
                    
                    # Change to current baudrate
                    self.set_baudrate(baudrate)
                    
                    # Small delay to let the baudrate change settle
                    time.sleep(0.05)
                    
                    # Clear any pending data in the input buffer
                    if self._comport_transport._serial:
                        self._comport_transport._serial.reset_input_buffer()
                    
                    # Send TesterPresent request with response required
                    try:
                        from kwp2000 import services
                        response = client.tester_present(
                            response_required=services.TesterPresent.ResponseRequired.YES,
                            timeout=timeout
                        )
                        
                        # If we get here, we received a response!
                        if verbose:
                            self.logger.info(f"Response received at {baudrate} baud")
                        found_baudrate = baudrate
                        break  # Found working baudrate, exit loop
                        
                    except TimeoutException:
                        # No response within timeout - continue to next baudrate
                        if verbose:
                            self.logger.debug(f"No response at {baudrate} baud")
                        continue
                        
                    except NegativeResponseException:
                        # Negative response means ECU is there but rejected the request
                        # This still indicates communication is working
                        if verbose:
                            self.logger.info(f"Negative response received at {baudrate} baud (ECU present)")
                        found_baudrate = baudrate
                        break  # Found working baudrate, exit loop
                        
                    except Exception as e:
                        # Other errors - log but continue
                        if verbose:
                            self.logger.debug(f"Error at {baudrate} baud: {type(e).__name__}")
                        continue
                        
                except TransportException as e:
                    if verbose:
                        self.logger.warning(f"Transport error at {baudrate} baud: {e}")
                    continue
                except Exception as e:
                    if verbose:
                        self.logger.warning(f"Unexpected error at {baudrate} baud: {type(e).__name__}: {e}")
                    continue
            
            # Return found baudrate (or None if none found)
            if found_baudrate is None:
                if verbose:
                    self.logger.warning("No working baudrate found")
                # Restore original baudrate if no working baudrate was found
                try:
                    if self._comport_transport._serial.baudrate != original_baudrate:
                        self.set_baudrate(original_baudrate)
                except Exception:
                    pass
            
            return found_baudrate
            
        except Exception as e:
            # On any unexpected error, try to restore original baudrate
            try:
                if self._comport_transport._serial.baudrate != original_baudrate:
                    self.set_baudrate(original_baudrate)
            except Exception:
                pass
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()



