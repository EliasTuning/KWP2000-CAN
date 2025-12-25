"""COM port transport layer for KWP2000 communication."""

import logging
from typing import Optional
from protocols.kwp2000 import Transport
from protocols.kwp2000 import TransportException

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
    COM port transport for KWP2000 communication.
    
    This transport sends and receives KWP2000 frames directly over a serial port.
    Unlike the J2534 transport, this implementation is not threaded and operates
    synchronously.
    
    Usage:
        transport = ComportTransport(port='COM3', baudrate=9600)
        with transport:
            transport.send(b'\\x10\\x89')
            data = transport.wait_frame(timeout=1.0)
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
        bytesize: int = serial.EIGHTBITS,
        parity: str = serial.PARITY_NONE,
        stopbits: float = serial.STOPBITS_TWO,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize COM port transport.
        
        Args:
            port: COM port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Baud rate (default: 9600)
            timeout: Default timeout in seconds for read operations
            bytesize: Number of data bits (default: 8)
            parity: Parity setting (default: NONE)
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
            #self._serial.reset_input_buffer()
            self._serial.read(len(data))
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
        
        This method reads raw bytes from the serial port without any
        modification or parsing.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Received bytes, or None if timeout occurs
            
        Raises:
            TransportException: If receive fails or transport is not open
        """
        if not self._is_open or not self._serial or not self._serial.is_open:
            raise TransportException("Transport not open")
        
        # Set read timeout
        original_timeout = self._serial.timeout
        self._serial.timeout = timeout
        
        try:
            # Read available data from serial port
            data = self._serial.read(1024)  # Read up to 1024 bytes
            
            if not data:
                return None
            
            self.logger.debug(f"Received {len(data)} bytes: {data.hex()}")
            return bytes(data)
            
        except serial.SerialException as e:
            raise TransportException(f"Serial read error: {e}") from e
        finally:
            # Restore original timeout
            self._serial.timeout = original_timeout
    
    def set_baudrate(self, baudrate: int) -> None:
        """
        Change the baudrate of the serial port connection.
        
        This method can be called while the port is open to dynamically change
        the baudrate. The serial port connection must be open.
        
        Args:
            baudrate: New baudrate value
            
        Raises:
            TransportException: If transport is not open or baudrate change fails
        """
        if not self._is_open or not self._serial or not self._serial.is_open:
            raise TransportException("Transport not open")
        
        try:
            # Update the serial port baudrate
            self._serial.baudrate = baudrate
            self.baudrate = baudrate
            self.logger.info(f"Changed COM port {self.port} baudrate to {baudrate}")
        except serial.SerialException as e:
            raise TransportException(f"Failed to change baudrate: {e}") from e
    
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
