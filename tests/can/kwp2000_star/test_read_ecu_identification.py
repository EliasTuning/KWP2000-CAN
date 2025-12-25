"""
Pytest tests for KWP2000-STAR communication over CAN bus.
Tests ECU identification reading functionality.
"""
import sys
from pathlib import Path

# Calculate paths
project_root = Path(__file__).parent.parent.parent.parent.resolve()
test_dir = Path(__file__).parent.parent.parent.resolve()  # tests/can
can_test_dir = Path(__file__).parent.parent.resolve()  # tests/can

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
modules_to_clear = ['kwp2000', 'kwp2000_star_can']
for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Import from project root packages
from protocols.can.kwp2000_star_can import KWP2000StarTransportCAN
from protocols.kwp2000 import KWP2000Client

# Add tests/can directory to path for mockup_can import (after main imports)
can_test_dir_str = str(can_test_dir)
if can_test_dir_str not in sys.path:
    sys.path.insert(0, can_test_dir_str)

from mockup_can import MockupCan
from message_parsers import parse_candump_messages


def test_read_ecu_identification():
    """Test reading ECU identification via KWP2000-STAR over CAN bus."""
    # Get the candump file path relative to this test file
    candump_path = Path(__file__).parent / 'can_messages.txt'
    
    # CAN IDs for KWP2000-STAR
    rx_id = 0x612  # ECU transmits on this ID
    tx_id = 0x6F1  # Tester transmits on this ID
    
    # Create parser function for candump format
    def load_messages():
        return parse_candump_messages(str(candump_path), tx_id=tx_id, rx_id=rx_id)
    
    # Initialize CAN connection with candump parser
    can_connection = MockupCan(parser=load_messages)
    
    # Create KWP2000-STAR transport layer
    transport = KWP2000StarTransportCAN(
        can_connection=can_connection,
        rx_id=rx_id,
        tx_id=tx_id
    )
    
    # Create KWP2000 client
    star_client = KWP2000Client(transport)
    
    # Use context managers
    with star_client:
        print("Connected via KWP2000-STAR over CAN bus")
        
        # Read data by local identifier
        data = star_client.read_ecu_identification(ecu_identification_option=0x80)
        
        # Assert data read successfully
        assert data is not None, "ECU identification response should not be None"
        assert hasattr(data, 'ecu_identification_data'), "Response should contain ecu_identification_data"
        assert isinstance(data.ecu_identification_data, bytes), "ECU identification data should be bytes"
        assert len(data.ecu_identification_data) > 0, "ECU identification data should not be empty"
        
        print(f"ECU identification data: {data.ecu_identification_data.hex(' ').upper()}")
        print("Test completed successfully!")

