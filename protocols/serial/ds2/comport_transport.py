"""COM port transport layer for DS2 communication."""

import logging
from typing import Optional

from ds2.exceptions import TransportException
from ds2.transport import Transport

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    raise ImportError(
        "pyserial is required for COM port transport. "
        "Install it with: pip install pyserial"
    )


class ComportTransport(Transport):
    """
    COM port transport for DS2 communication.
    
    This transport sends and receives DS2 frames directly over a serial port.
    DS2 uses 9600 baud, 8 data bits, even parity, 1 stop bit.
    
    Usage:
        transport = ComportTransport(port='COM3', baudrate=9600)
        with transport:
            transport.send(b'\\x80\\x05\\x0c\\x0a\\x00\\x64\\xXX')
            data = transport.wait_frame(timeout=1.0)
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
        bytesize: int = serial.EIGHTBITS,
        parity: int = serial.PARITY_EVEN,
        stopbits: float = serial.STOPBITS_TWO,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize COM port transport.
        
        Args:
            port: COM port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Baud rate (default: 9600 for DS2)
            timeout: Default timeout in seconds for read operations
            bytesize: Number of data bits (default: 8)
            parity: Parity setting (default: EVEN for DS2)
            stopbits: Number of stop bits (default: 1)
            logger: Optional logger instance (default: root logger)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.logger = logger if logger is not None else logging.getLogger(__name__)
        
        self._serial: Optional[serial.Serial] = None
        self._is_open = False
    
    def open(self) -> None:
        """Open the serial port connection."""
        if self._is_open:
            return
        
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout
            )
            self._is_open = True
            self.logger.info(
                f"Opened COM port {self.port} at {self.baudrate} baud"
            )
        except serial.SerialException as e:
            raise TransportException(f"Failed to open COM port {self.port}: {e}") from e
    
    def close(self) -> None:
        """Close the serial port connection."""
        if not self._is_open:
            return
        
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._is_open = False
            self.logger.info(f"Closed COM port {self.port}")
        except Exception as e:
            self.logger.warning(f"Error closing COM port: {e}")
        finally:
            self._serial = None
    
    def send(self, data: bytes) -> None:
        """
        Send raw bytes over the serial port.
        
        This method sends the data bytes directly to the serial port without
        any modification or framing.
        
        Args:
            data: Raw bytes to send
            
        Raises:
            TransportException: If send fails or transport is not open
        """
        if not self._is_open or not self._serial or not self._serial.is_open:
            raise TransportException("Transport not open")
        
        try:
            bytes_written = self._serial.write(data)
            self._serial.flush()  # Ensure data is sent immediately
            self.logger.debug(f"Sent {bytes_written} bytes: {data.hex()}")
            
            if bytes_written != len(data):
                raise TransportException(
                    f"Partial write: wrote {bytes_written} of {len(data)} bytes"
                )
        except serial.SerialException as e:
            raise TransportException(f"Serial write error: {e}") from e
    
    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive data from the serial port.
        
        DS2 protocol:
        1. Read address byte
        2. Read size byte
        3. Read remaining bytes (size - 3)
        4. Verify checksum
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Received frame bytes, or None if timeout occurs
            
        Raises:
            TransportException: If receive fails or transport is not open
        """
        if not self._is_open or not self._serial or not self._serial.is_open:
            raise TransportException("Transport not open")
        
        # Set read timeout
        original_timeout = self._serial.timeout
        self._serial.timeout = timeout
        
        try:
            # Read address byte
            address_data = self._serial.read(1)
            if not address_data:
                return None
            
            address = address_data[0]
            
            # Read size byte
            size_data = self._serial.read(1)
            if not size_data:
                return None
            
            size = size_data[0]
            
            # Read remaining bytes (size - 3, since we already read address and size)
            remaining = size - 3
            if remaining > 0:
                payload = self._serial.read(remaining)
                if len(payload) < remaining:
                    return None
            else:
                payload = b''
            
            # Read checksum
            checksum_data = self._serial.read(1)
            if not checksum_data:
                return None
            
            # Build complete frame
            frame = bytes([address, size]) + payload + checksum_data
            
            # Reset input buffer (as done in original implementation)
            self._serial.reset_input_buffer()
            
            self.logger.debug(f"Received {len(frame)} bytes: {frame.hex()}")
            return frame
            
        except serial.SerialException as e:
            raise TransportException(f"Serial read error: {e}") from e
        finally:
            # Restore original timeout
            self._serial.timeout = original_timeout
    
    @staticmethod
    def list_ports() -> list:
        """
        List available COM ports.
        
        Returns:
            List of available port names
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
