"""
Pytest tests for KWP2000-STAR communication over serial port.
Tests STAR framing and diagnostic session functionality.
"""
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import patch

# Calculate paths
project_root = Path(__file__).parent.parent.parent.parent.resolve()
test_dir = Path(__file__).parent.parent.parent.resolve()  # tests/serial

# Remove any conflicting paths that might interfere with imports
conflicting_paths = [
    str(test_dir / 'kwp2000_star'),
    str(test_dir),
]
for path in conflicting_paths:
    normalized_path = str(Path(path).resolve())
    if normalized_path in sys.path:
        sys.path.remove(normalized_path)

# Ensure project root is at the beginning of sys.path (highest priority)
project_root_str = str(project_root)
if project_root_str in sys.path:
    sys.path.remove(project_root_str)
sys.path.insert(0, project_root_str)

# Clear any cached imports that might have been loaded from wrong location
modules_to_clear = ['kwp2000_star_serial', 'kwp2000']
for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Import from project root packages
from protocols.kwp2000 import Transport, TransportException
from protocols.kwp2000.client import KWP2000Client
from protocols.kwp2000.constants import (
    SERVICE_START_DIAGNOSTIC_SESSION,
    RESPONSE_POSITIVE
)
from protocols.serial.kwp2000_star_serial.transport import KWP2000StarTransport
from protocols.serial.kwp2000_star_serial.frames import build_frame, parse_frame


class MockComportTransport(Transport):
    """
    Mock COM port transport for testing KWP2000-STAR.
    
    Implements the Transport interface used by KWP2000StarTransport.
    """
    
    def __init__(self):
        self._sent_frames = []
        self._response_queue = []
        self._is_open = False
        self.baudrate = 9600
    
    def open(self) -> None:
        """Open the mock transport."""
        self._is_open = True
        self._sent_frames.clear()
        self._response_queue.clear()
    
    def close(self) -> None:
        """Close the mock transport."""
        self._is_open = False
    
    def send(self, data: bytes) -> None:
        """Store sent frame (STAR frame)."""
        if not self._is_open:
            raise TransportException("Transport not open")
        self._sent_frames.append(data)
    
    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Return next STAR frame from response queue.
        
        Args:
            timeout: Ignored in mock, but kept for API compatibility
            
        Returns:
            Next STAR frame from queue, or None if queue is empty
        """
        if not self._is_open:
            raise TransportException("Transport not open")
        
        if self._response_queue:
            return self._response_queue.pop(0)
        return None
    
    def queue_response(self, star_frame: bytes) -> None:
        """
        Queue a STAR frame to be returned by wait_frame.
        
        Args:
            star_frame: Complete STAR frame bytes (with framing)
        """
        self._response_queue.append(star_frame)
    
    def get_sent_frames(self) -> list:
        """
        Get all STAR frames that were sent.
        
        Returns:
            List of sent STAR frame bytes
        """
        return self._sent_frames.copy()
    
    def set_baudrate(self, baudrate: int) -> None:
        """
        Change the baudrate (for compatibility with ComportTransport interface).
        
        Args:
            baudrate: New baudrate value
        """
        self.baudrate = baudrate


def test_diagnostic_session():
    """Test KWP2000-STAR diagnostic session with STAR framing."""
    # Create mock COM port transport
    mock_comport = MockComportTransport()
    
    # Create KWP2000-STAR transport with mock COM port
    # We'll patch the ComportTransport creation to use our mock
    transport = KWP2000StarTransport(
        port='COM1',  # Dummy port, won't be used
        baudrate=9600
    )
    
    # Replace the internal comport transport with our mock
    transport._comport_transport = mock_comport
    
    # Create KWP2000 client
    client = KWP2000Client(transport)
    
    # Use context managers
    with client:
        print("Connected via KWP2000-STAR serial")
        
        # Start diagnostic session (0x10 0x89)
        session_type = 0x89
        
        # Prepare KWP2000 service payload (without STAR framing)
        # This is what KWP2000Client will send via transport.send()
        service_payload = bytes([SERVICE_START_DIAGNOSTIC_SESSION, session_type])
        
        # The transport will wrap this in a STAR frame
        # So we need to queue a STAR frame response
        # Positive response: service_id = 0x10 + 0x40 = 0x50
        # Response data: [session_type_echo]
        response_service_payload = bytes([RESPONSE_POSITIVE + SERVICE_START_DIAGNOSTIC_SESSION]) + bytes([session_type])
        
        # Build STAR frame for response
        response_star_frame = build_frame(response_service_payload)
        mock_comport.queue_response(response_star_frame)
        
        # Call startDiagnosticSession
        # This will:
        # 1. Send service_payload via transport.send()
        # 2. transport.send() wraps it in STAR frame and calls mock_comport.send()
        # 3. transport.wait_frame() calls mock_comport.wait_frame() and parses STAR frame
        session_response = client.startDiagnosticSession(session_type=session_type)
        
        # Assert session started successfully
        assert session_response is not None, "Session response should not be None"
        assert 'session_type_echo' in session_response, "Session response should contain session_type_echo"
        assert session_response.get('session_type_echo') == session_type, \
            f"Expected session type echo 0x{session_type:02X}, got 0x{session_response.get('session_type_echo', 0):02X}"
        
        # Verify that a STAR frame was sent
        sent_frames = mock_comport.get_sent_frames()
        assert len(sent_frames) == 1, f"Expected 1 sent frame, got {len(sent_frames)}"
        
        # Parse the sent STAR frame to verify it contains the service payload
        sent_star_frame = sent_frames[0]
        parsed_payload, = parse_frame(sent_star_frame)
        assert parsed_payload == service_payload, \
            f"Expected service payload {service_payload.hex()}, got {parsed_payload.hex()}"
        
        print(f"Session started: session_type_echo=0x{session_response.get('session_type_echo'):02X}")
        print(f"Sent STAR frame: {sent_star_frame.hex(' ').upper()}")
        print(f"Parsed payload from sent frame: {parsed_payload.hex(' ').upper()}")
        print("Test completed successfully!")

