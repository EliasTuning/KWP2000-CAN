"""Transport layer abstraction for KWP2000."""

from abc import ABC, abstractmethod
from typing import Optional
import time
from kwp2000.exceptions import TimeoutException, TransportException


class Transport(ABC):
    """
    Abstract base class for KWP2000 transport implementations.
    
    This provides the raw connection interface for sending and receiving frames.
    """
    
    @abstractmethod
    def send(self, data: bytes) -> None:
        """
        Send raw bytes over the transport.
        
        Args:
            data: Raw bytes to send (complete frame)
            
        Raises:
            TransportException: If send fails
        """
        pass
    
    @abstractmethod
    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive a frame.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Received frame bytes, or None if timeout occurs
            
        Raises:
            TimeoutException: If timeout occurs (if None not returned)
            TransportException: If receive fails
        """
        pass
    
    @abstractmethod
    def open(self) -> None:
        """Open the transport connection."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the transport connection."""
        pass
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MockTransport(Transport):
    """
    Mock transport for testing and examples.
    
    Stores sent frames and can be configured to return specific responses.
    """
    
    def __init__(self):
        self._sent_frames = []
        self._response_queue = []
        self._is_open = False
    
    def open(self) -> None:
        """Open the mock transport."""
        self._is_open = True
        self._sent_frames.clear()
        self._response_queue.clear()
    
    def close(self) -> None:
        """Close the mock transport."""
        self._is_open = False
    
    def send(self, data: bytes) -> None:
        """Store sent frame."""
        if not self._is_open:
            raise TransportException("Transport not open")
        self._sent_frames.append(data)
    
    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Return next frame from response queue.
        
        Args:
            timeout: Ignored in mock, but kept for API compatibility
            
        Returns:
            Next frame from queue, or None if queue is empty
        """
        if not self._is_open:
            raise TransportException("Transport not open")
        
        if self._response_queue:
            return self._response_queue.pop(0)
        return None
    
    def queue_response(self, frame: bytes) -> None:
        """
        Queue a response frame to be returned by wait_frame.
        
        Args:
            frame: Frame bytes to queue
        """
        self._response_queue.append(frame)
    
    def get_sent_frames(self) -> list:
        """
        Get all frames that were sent.
        
        Returns:
            List of sent frame bytes
        """
        return self._sent_frames.copy()
    
    def clear(self) -> None:
        """Clear sent frames and response queue."""
        self._sent_frames.clear()
        self._response_queue.clear()

