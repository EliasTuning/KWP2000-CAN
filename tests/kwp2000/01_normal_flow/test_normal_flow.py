"""
Pytest tests for normal flow KWP2000 communication over TP20 transport protocol.
Tests diagnostic session start and data reading functionality.
"""
import sys
import importlib
from pathlib import Path

# Calculate paths
project_root = Path(__file__).parent.parent.parent.parent.resolve()
test_dir = Path(__file__).parent.parent.parent.resolve()

# Remove any conflicting paths that might interfere with imports
# Pytest may add test directories to sys.path, which can cause import conflicts
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
modules_to_clear = ['kwp2000', 'tp20']
for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Import from project root packages
from tp20 import TP20Transport
from kwp2000 import KWP2000Client

# Add tests directory to path for mockup_can import (after main imports)
test_dir_str = str(test_dir)
if test_dir_str not in sys.path:
    sys.path.insert(0, test_dir_str)

from mockup_can import MockupCan


def test_normal_flow_diagnostic_session_and_read_data():
    """Test normal flow: start diagnostic session and read data by local identifier."""
    # Get the CSV path relative to this test file
    csv_path = Path(__file__).parent / 'can_messages.csv'
    
    # Initialize CSV-based CAN connection
    can_connection = MockupCan(str(csv_path))
    
    # Create TP20 transport layer
    tp20 = TP20Transport(
        can_connection=can_connection,
        dest=0x01,
    )
    
    # Create KWP2000 client
    kwp2000_client = KWP2000Client(tp20)
    
    # Use context managers
    with tp20:
        with kwp2000_client:
            # Start diagnostic session (0x10 0x89)
            session_response = kwp2000_client.startDiagnosticSession(session_type=0x89)
            
            # Assert session started successfully
            assert session_response is not None, "Session response should not be None"
            assert 'session_type_echo' in session_response, "Session response should contain session_type_echo"
            assert session_response.get('session_type_echo') == 0x89, \
                f"Expected session type echo 0x89, got 0x{session_response.get('session_type_echo', 0):02X}"
            
            # Read data by local identifier (0x21 0x01)
            data_response = kwp2000_client.readDataByLocalIdentifier(local_identifier=0x01)
            
            # Assert data read successfully
            assert data_response is not None, "Data response should not be None"
            assert 'local_identifier_echo' in data_response, "Data response should contain local_identifier_echo"
            assert data_response.get('local_identifier_echo') == 0x01, \
                f"Expected local identifier echo 0x01, got 0x{data_response.get('local_identifier_echo', 0):02X}"
            assert 'data' in data_response, "Data response should contain data"
            assert isinstance(data_response['data'], bytes), "Data should be bytes"




