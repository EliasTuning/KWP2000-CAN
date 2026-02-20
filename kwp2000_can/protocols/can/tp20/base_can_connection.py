"""CAN connection interface for TP20."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from tp20.exceptions import TP20Exception


def _tp20_exception(message: str) -> "TP20Exception":
    """Lazily import TP20Exception to avoid circular imports during module load."""
    from tp20.exceptions import TP20Exception
    return TP20Exception(message)




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
            raise _tp20_exception("CAN connection not open")
        if len(data) > 8:
            raise _tp20_exception(f"CAN frame data too long: {len(data)} bytes (max 8)")
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
            raise _tp20_exception("CAN connection not open")
        
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


class proxy_can(CanConnection):
    """
    Proxy CAN connection that delegates to another CanConnection and logs
    all CAN messages to a separate file.
    """

    def __init__(self, delegate: CanConnection, log_path: str = "can_messages.log"):
        """
        Args:
            delegate: The CanConnection instance to delegate all operations to.
            log_path: Path to the file where CAN messages are logged.
        """
        self._delegate = delegate
        self._log_path = log_path
        self._log_file = None

    def _log_frame(self, direction: str, can_id: int, data: bytes) -> None:
        """Write a single CAN frame line to the log file."""
        if self._log_file is None:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        hex_data = data.hex().upper() if data else ""
        line = f"{ts} {direction} id=0x{can_id:03X} data={hex_data}\n"
        try:
            self._log_file.write(line)
            self._log_file.flush()
        except OSError:
            pass

    def open(self) -> None:
        """Open the delegate and the log file."""
        self._delegate.open()
        self._log_file = open(self._log_path, "a", encoding="utf-8")

    def close(self) -> None:
        """Close the log file and the delegate."""
        if self._log_file is not None:
            try:
                self._log_file.close()
            except OSError:
                pass
            self._log_file = None
        self._delegate.close()

    def send_can_frame(self, can_id: int, data: bytes) -> None:
        """Log the frame and delegate send to the underlying connection."""
        self._log_frame("TX", can_id, data)
        self._delegate.send_can_frame(can_id, data)

    def recv_can_frame(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """Delegate receive and log the frame if one is received."""
        result = self._delegate.recv_can_frame(timeout=timeout)
        if result is not None:
            can_id, data = result
            self._log_frame("RX", can_id, data)
        return result

