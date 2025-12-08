"""Transport layer for KWP2000-STAR protocol over COM port."""

import logging
from typing import Optional
from kwp2000.transport import Transport
from kwp2000.exceptions import TransportException
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
            print(star_frame.hex())
            
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
            timeout: Maximum time to wait in seconds
            
        Returns:
            KWP2000 service data bytes (payload), or None if timeout occurs
            
        Raises:
            TransportException: If receive fails or transport is not open
        """
        if not self._is_open:
            raise TransportException("Transport not open")
        
        try:
            # Receive STAR frame from COM port transport
            star_frame = self._comport_transport.wait_frame(timeout=timeout)
            
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
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

