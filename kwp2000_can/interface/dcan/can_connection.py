"""DCAN CAN connection adapter for KWP2000-CAN."""

import logging
from typing import Optional, Tuple

from kwp2000_can.interface.base_can_connection import CanConnection
from .can_adapter import CanAdapter, CanAdapterError, CanAdapterTimeout


class DCanCanConnection(CanConnection):
    """
    DCAN-based CAN connection adapter for KWP2000-CAN.
    
    Implements the CanConnection interface by wrapping CanAdapter,
    converting between standard CAN frame format (can_id, data) and
    DCAN's target/source address format.
    
    Usage:
        can_conn = DCanCanConnection(port='COM3', baudrate=115200)
        can_conn.open()
        can_conn.send_can_frame(0x612, b'\\x01\\x02\\x03')
        frame = can_conn.recv_can_frame(timeout=1.0)
        can_conn.close()
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        rx_id: int = 0x612,
        tx_id: int = 0x6F1,
        debug: bool = False,
        logger: logging.Logger = None
    ):
        """
        Initialize DCAN CAN connection adapter.
        
        Args:
            port: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Serial baud rate (default: 115200)
            timeout: Serial read timeout in seconds (default: 1.0)
            rx_id: CAN ID to receive frames on (default: 0x612)
            tx_id: CAN ID to send frames on (default: 0x6F1)
            debug: Enable debug logging (default: False)
            logger: Optional logger instance (default: root logger)
        """
        self.logger = logger if logger is not None else logging.getLogger(__name__)
        self._adapter = CanAdapter()
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._rx_id = rx_id
        self._tx_id = tx_id
        self._debug = debug
        self._is_open = False
    
    def open(self) -> None:
        """Open the CAN connection."""
        if self._is_open:
            return
        
        try:
            self._adapter.open(
                port=self._port,
                baudrate=self._baudrate,
                timeout=self._timeout
            )
            self._is_open = True
            self.logger.info(f"DCanCanConnection opened on {self._port}")
        except CanAdapterError as e:
            raise Exception(f"Failed to open DCAN connection: {e}") from e
    
    def close(self) -> None:
        """Close the CAN connection."""
        if not self._is_open:
            return
        
        try:
            self._adapter.close()
            self._is_open = False
            self.logger.info("DCanCanConnection closed")
        except Exception as e:
            self.logger.warning(f"Error closing DCAN connection: {e}")
            self._is_open = False
    
    def send_can_frame(self, can_id: int, data: bytes) -> None:
        """
        Send a CAN frame.
        
        Args:
            can_id: CAN ID (11-bit or 29-bit) - should match tx_id for proper addressing
            data: Data payload (up to 8 bytes for standard CAN, but DCAN supports up to 255 bytes)
            
        Raises:
            Exception: If send fails or connection not open
        """
        if not self._is_open:
            raise Exception("CAN connection not open")
        
        # Extract target and source addresses from CAN IDs
        # For KWP2000-STAR over DCAN:
        # - tx_id (e.g., 0x6F1) -> target address is lower 8 bits (0xF1)
        # - source address is typically 0xF1 for tester
        # The can_id should match tx_id when sending
        if can_id != self._tx_id:
            self.logger.warning(f"Sending frame with CAN ID 0x{can_id:X}, but tx_id is 0x{self._tx_id:X}")
        
        # Extract target address from CAN ID (lower 8 bits)
        target = can_id & 0xFF
        # Source address is typically 0xF1 for tester
        source = 0xF1
        
        try:
            self._adapter.can_send(target=target, source=source, data=data)
        except CanAdapterError as e:
            raise Exception(f"Failed to send CAN frame: {e}") from e
    
    def recv_can_frame(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """
        Receive a CAN frame.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Tuple of (can_id, data) or None if timeout occurs
            
        Raises:
            Exception: If receive fails or connection not open
        """
        if not self._is_open:
            raise Exception("CAN connection not open")
        
        try:
            target, source, data = self._adapter.can_recv(timeout=timeout)
            
            # Reconstruct CAN ID from received frame
            # For KWP2000-STAR, frames received from ECU have:
            # - target = lower 8 bits of rx_id (where ECU sends to)
            # - source = ECU address (typically 0x12 for some ECUs)
            # We return rx_id as the CAN ID since that's what we're listening on
            # The target address should match the lower 8 bits of rx_id
            expected_target = self._rx_id & 0xFF
            if target != expected_target:
                self.logger.debug(f"Received frame with target 0x{target:02X}, expected 0x{expected_target:02X}")
            
            # Return the rx_id as the CAN ID
            return (self._rx_id, data)
        except CanAdapterTimeout:
            return None
        except CanAdapterError as e:
            raise Exception(f"Failed to receive CAN frame: {e}") from e

