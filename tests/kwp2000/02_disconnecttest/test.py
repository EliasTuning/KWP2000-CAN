"""
Main tests script that simulates a tester sending and receiving CAN messages
using the TP20 transport protocol implementation with KWP2000.
"""
import sys
from pathlib import Path

# Add parent directories to path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add tests/kwp2000 directory to path for base_test import
kwp2000_test_dir = Path(__file__).parent.parent
sys.path.insert(0, str(kwp2000_test_dir))

from base_test import simulate_tester_base


def test_logic(tp20, kwp2000_client):
    """Test-specific logic for disconnect tests."""
    # Start diagnostic session (0x10 0x89)
    print("Starting diagnostic session (0x89)...")
    try:
        session_response = kwp2000_client.startDiagnosticSession(session_type=0x89)
        print(f"Diagnostic session started successfully!")
        print(f"Session type echo: 0x{session_response.get('session_type_echo', 0):02X}\n")
    except Exception as e:
        print(f"Error starting diagnostic session: {e}\n")
    
    # Read data by local identifier (0x21 0x01)
    print("Reading data by local identifier (0x01)...")
    try:
        data_response = kwp2000_client.readDataByLocalIdentifier(local_identifier=0x01)
        print(f"Data read successfully!")
        print(f"Local identifier echo: 0x{data_response.get('local_identifier_echo', 0):02X}")
        if 'data' in data_response:
            data_bytes = data_response['data']
            print(f"Data: {data_bytes.hex(' ').upper()}\n")
    except Exception as e:
        print(f"Error reading data: {e}\n")


def simulate_tester():
    """Simulate a tester sending messages and receiving responses using KWP2000 over TP20."""
    simulate_tester_base('can_messages.csv', dest=0x01, test_logic=test_logic)


if __name__ == "__main__":
    simulate_tester()

