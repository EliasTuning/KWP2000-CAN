"""J2534 CAN connection adapter for TP20."""

import queue
import time
from typing import Optional, Tuple
import logging

from tp20.can_connection import CanConnection
from tp20.exceptions import TP20Exception
from .j2534_connection import J2534Connection


class J2534CanConnection(CanConnection):
    """
    J2534-based CAN connection adapter for TP20.
    
    Implements the CanConnection interface by wrapping J2534Connection,
    converting between TP20's CAN frame format and J2534's raw byte format.
    
    Usage:
        can_conn = J2534CanConnection(dll_path="path/to/dll.dll")
        can_conn.open()
        can_conn.send_can_frame(0x300, b'\\x01\\x02\\x03')
        frame = can_conn.recv_can_frame(timeout=1.0)
        can_conn.close()
    """
    
    def __init__(
        self,
        dll_path: str = None,
        baudrate: int = 500000,
        debug: bool = False,
        logger: logging.Logger = None
    ):
        """
        Initialize J2534 CAN connection adapter.
        
        Args:
            dll_path: Path to J2534 DLL (optional, will auto-detect if None)
            baudrate: CAN bus baud rate (default: 500000)
            debug: Enable debug logging (default: False)
            logger: Optional logger instance (default: root logger)
        """
        self.logger = logger if logger is not None else logging.getLogger()
        self._j2534_conn = J2534Connection(
            dll_path=dll_path,
            baudrate=baudrate,
            debug=debug,
            logger=self.logger
        )
        self._is_open = False
    
    def open(self) -> None:
        """Open the CAN connection."""
        if self._is_open:
            return
        
        self._j2534_conn.open()
        self._is_open = True
        self.logger.info("J2534CanConnection opened")
    
    def close(self) -> None:
        """Close the CAN connection."""
        if not self._is_open:
            return
        
        self._j2534_conn.close()
        self._is_open = False
        self.logger.info("J2534CanConnection closed")
    
    def send_can_frame(self, can_id: int, data: bytes) -> None:
        """
        Send a CAN frame.
        
        Args:
            can_id: CAN ID (11-bit or 29-bit)
            data: Data payload (up to 8 bytes)
            
        Raises:
            TP20Exception: If send fails or connection not open
        """
        if not self._is_open:
            raise TP20Exception("CAN connection not open")
        
        if len(data) > 8:
            raise TP20Exception(f"CAN frame data too long: {len(data)} bytes (max 8)")
        
        # J2534 expects: 4-byte CAN ID (big-endian) + data
        can_id_bytes = can_id.to_bytes(4, "big")
        payload = can_id_bytes + data
        
        try:
            self._j2534_conn.specific_send(payload)
        except Exception as e:
            raise TP20Exception(f"Failed to send CAN frame: {e}") from e
    
    def recv_can_frame(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """
        Receive a CAN frame.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Tuple of (can_id, data) or None if timeout occurs
            
        Raises:
            TP20Exception: If receive fails or connection not open
        """
        if not self._is_open:
            raise TP20Exception("CAN connection not open")
        
        try:
            # J2534 returns: 4-byte CAN ID (big-endian) + data
            frame = self._j2534_conn.specific_wait_frame(timeout=timeout)
            
            if frame is None:
                return None
            
            if len(frame) < 4:
                self.logger.warning(f"Received frame too short: {len(frame)} bytes")
                return None
            
            # Extract CAN ID and data
            can_id = int.from_bytes(frame[0:4], "big")
            can_data = frame[4:]
            
            return (can_id, can_data)
        except Exception as e:
            raise TP20Exception(f"Failed to receive CAN frame: {e}") from e

