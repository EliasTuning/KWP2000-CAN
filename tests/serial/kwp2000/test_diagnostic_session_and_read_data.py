"""
Pytest tests for KWP2000 communication over serial port.
Tests diagnostic session start and data reading functionality.
"""
import sys
from pathlib import Path

# Calculate paths
project_root = Path(__file__).parent.parent.parent.parent.resolve()
test_dir = Path(__file__).parent.parent.parent.resolve()  # tests/serial

# Remove any conflicting paths that might interfere with imports
conflicting_paths = [
    str(test_dir / 'kwp2000'),
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
modules_to_clear = ['kwp2000']
for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Import from project root packages
from protocols.kwp2000.transport import MockTransport
from protocols.kwp2000.client import KWP2000Client
from protocols.kwp2000.constants import (
    SERVICE_START_DIAGNOSTIC_SESSION,
    SERVICE_READ_DATA_BY_LOCAL_IDENTIFIER,
    RESPONSE_POSITIVE
)


def test_diagnostic_session_and_read_data():
    """Test normal flow: start diagnostic session and read data by local identifier."""
    # Create mock transport
    transport = MockTransport()
    
    # Create KWP2000 client
    kwp2000_client = KWP2000Client(transport)
    
    # Use context managers
    with kwp2000_client:
        print("Connected via KWP2000 serial")
        
        # Start diagnostic session (0x10 0x89)
        session_type = 0x89
        
        # Queue response for startDiagnosticSession
        # Positive response: service_id = 0x10 + 0x40 = 0x50
        # Response data: [session_type_echo]
        session_response_payload = bytes([RESPONSE_POSITIVE + SERVICE_START_DIAGNOSTIC_SESSION]) + bytes([session_type])
        transport.queue_response(session_response_payload)
        
        session_response = kwp2000_client.startDiagnosticSession(session_type=session_type)
        
        # Assert session started successfully
        assert session_response is not None, "Session response should not be None"
        assert 'session_type_echo' in session_response, "Session response should contain session_type_echo"
        assert session_response.get('session_type_echo') == session_type, \
            f"Expected session type echo 0x{session_type:02X}, got 0x{session_response.get('session_type_echo', 0):02X}"
        
        print(f"Session started: session_type_echo=0x{session_response.get('session_type_echo'):02X}")
        
        # Read data by local identifier (0x21 0x01)
        local_identifier = 0x01
        read_data = bytes([0x12, 0x34, 0x56, 0x78])  # Example data
        
        # Queue response for readDataByLocalIdentifier
        # Positive response: service_id = 0x21 + 0x40 = 0x61
        # Response data: [local_identifier_echo, data...]
        read_response_payload = bytes([RESPONSE_POSITIVE + SERVICE_READ_DATA_BY_LOCAL_IDENTIFIER]) + \
                                bytes([local_identifier]) + read_data
        transport.queue_response(read_response_payload)
        
        data_response = kwp2000_client.readDataByLocalIdentifier(local_identifier=local_identifier)
        
        # Assert data read successfully
        assert data_response is not None, "Data response should not be None"
        assert 'local_identifier_echo' in data_response, "Data response should contain local_identifier_echo"
        assert data_response.get('local_identifier_echo') == local_identifier, \
            f"Expected local identifier echo 0x{local_identifier:02X}, got 0x{data_response.get('local_identifier_echo', 0):02X}"
        assert 'data' in data_response, "Data response should contain data"
        assert isinstance(data_response['data'], bytes), "Data should be bytes"
        assert data_response['data'] == read_data, \
            f"Expected data {read_data.hex()}, got {data_response['data'].hex()}"
        
        print(f"Data read: local_identifier_echo=0x{data_response.get('local_identifier_echo'):02X}")
        print(f"Data ({len(data_response['data'])} bytes): {data_response['data'].hex(' ').upper()}")
        print("Test completed successfully!")

