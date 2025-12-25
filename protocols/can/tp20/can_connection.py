"""CAN connection interface for TP20."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from tp20.exceptions import TP20Exception


class CanConnection(ABC):
    """
    Abstract base class for CAN bus connections.
    
    This provides the interface for sending and receiving CAN frames
    that TP20Transport uses to communicate over CAN bus.
    """
    
    @abstractmethod
    def send_can_frame(self, can_id: int, data: bytes) -> None:
        """
        Send a CAN frame.
        
        Args:
            can_id: CAN ID (11-bit or 29-bit)
            data: Data payload (up to 8 bytes)
            
        Raises:
            TP20Exception: If send fails
        """
        pass
    
    @abstractmethod
    def recv_can_frame(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """
        Receive a CAN frame.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Tuple of (can_id, data) or None if timeout occurs
            
        Raises:
            TP20Exception: If receive fails
        """
        pass
    
    @abstractmethod
    def open(self) -> None:
        """Open the CAN connection."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the CAN connection."""
        pass
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MockCanConnection(CanConnection):
    """
    Mock CAN connection for testing and examples.
    
    Stores sent frames and can be configured to return specific responses.
    """
    
    def __init__(self):
        self._sent_frames = []
        self._response_queue = []
        self._is_open = False
    
    def open(self) -> None:
        """Open the mock CAN connection."""
        self._is_open = True
        self._sent_frames.clear()
        self._response_queue.clear()
    
    def close(self) -> None:
        """Close the mock CAN connection."""
        self._is_open = False
    
    def send_can_frame(self, can_id: int, data: bytes) -> None:
        """Store sent CAN frame."""
        if not self._is_open:
            raise TP20Exception("CAN connection not open")
        if len(data) > 8:
            raise TP20Exception(f"CAN frame data too long: {len(data)} bytes (max 8)")
        self._sent_frames.append((can_id, data))
    
    def recv_can_frame(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """
        Return next frame from response queue.
        
        Args:
            timeout: Ignored in mock, but kept for API compatibility
            
        Returns:
            Next frame from queue as (can_id, data), or None if queue is empty
        """
        if not self._is_open:
            raise TP20Exception("CAN connection not open")
        
        if self._response_queue:
            return self._response_queue.pop(0)
        return None
    
    def queue_response(self, can_id: int, data: bytes) -> None:
        """
        Queue a response frame to be returned by recv_can_frame.
        
        Args:
            can_id: CAN ID
            data: Data payload (up to 8 bytes)
        """
        if len(data) > 8:
            raise ValueError(f"CAN frame data too long: {len(data)} bytes (max 8)")
        self._response_queue.append((can_id, data))
    
    def get_sent_frames(self) -> list:
        """
        Get all frames that were sent.
        
        Returns:
            List of (can_id, data) tuples
        """
        return self._sent_frames.copy()
    
    def clear(self) -> None:
        """Clear sent frames and response queue."""
        self._sent_frames.clear()
        self._response_queue.clear()

