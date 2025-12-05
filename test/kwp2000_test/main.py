"""
Main test script that simulates a tester sending and receiving CAN messages
using the TP20 transport protocol implementation with KWP2000.
"""
import sys
from pathlib import Path

# Add parent directories to path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tp20 import TP20Transport
from kwp2000 import KWP2000Client
from mockup_can import MockupCan


def simulate_tester():
    """Simulate a tester sending messages and receiving responses using KWP2000 over TP20."""
    # Initialize CSV-based CAN connection
    # Path relative to this test file (same directory)
    csv_path = Path(__file__).parent / 'can_messages.csv'
    can_connection = MockupCan(str(csv_path))
    
    # Create TP20 transport layer
    # dest=0x01 is the ECU logical address
    # rx_id=0x300 is where we want ECU to transmit (we listen here)
    # tx_id=0x740 is where we transmit (ECU listens here)
    tp20 = TP20Transport(
        can_connection=can_connection,
        dest=0x01,
    )
    
    # Create KWP2000 client - TP20Transport can be used directly
    kwp2000_client = KWP2000Client(tp20)
    
    # Use context managers as requested
    with tp20 as tp20:
        with kwp2000_client as kwp2000_client:
            print("TP20 channel and KWP2000 client established successfully!\n")
            
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
            
            print("Test completed successfully!")


if __name__ == "__main__":
    simulate_tester()

