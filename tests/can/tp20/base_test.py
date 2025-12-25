"""
Base tests class for KWP2000 tests using TP20 transport protocol.
Provides common setup and initialization functionality.
"""
import sys
from pathlib import Path
from typing import Optional

# Add parent directories to path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from protocols.can.tp20 import TP20Transport
from protocols.kwp2000 import KWP2000Client

# Add tests directory to path for mockup_can import
test_dir = Path(__file__).parent.parent
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))

from mockup_can import MockupCan


class BaseKWP2000Test:
    """Base class for KWP2000 tests with common setup and teardown."""
    
    def __init__(self, csv_filename: str, dest: int = 0x01):
        """
        Initialize the base tests.
        
        Args:
            csv_filename: Path to the CSV file containing CAN messages (relative to tests file)
            dest: ECU logical address (default: 0x01)
        """
        self.csv_filename = csv_filename
        self.dest = dest
        self.can_connection: Optional[MockupCan] = None
        self.tp20: Optional[TP20Transport] = None
        self.kwp2000_client: Optional[KWP2000Client] = None
    
    def setup(self):
        """Set up the tests environment."""
        # Get the CSV path relative to the calling tests file
        # This assumes the CSV is in the same directory as the tests file
        test_file_path = Path(sys._getframe(1).f_globals.get('__file__', ''))
        csv_path = test_file_path.parent / self.csv_filename
        
        # Initialize CSV-based CAN connection
        self.can_connection = MockupCan(str(csv_path))
        
        # Create TP20 transport layer
        # dest=0x01 is the ECU logical address
        # rx_id=0x300 is where we want ECU to transmit (we listen here)
        # tx_id=0x740 is where we transmit (ECU listens here)
        self.tp20 = TP20Transport(
            can_connection=self.can_connection,
            dest=self.dest,
        )
        
        # Create KWP2000 client - TP20Transport can be used directly
        self.kwp2000_client = KWP2000Client(self.tp20)
    
    def teardown(self):
        """Clean up tests resources."""
        if self.kwp2000_client:
            self.kwp2000_client = None
        if self.tp20:
            self.tp20 = None
        if self.can_connection:
            self.can_connection = None
    
    def run_test(self):
        """
        Run the tests. Override this method in subclasses to implement tests-specific logic.
        """
        raise NotImplementedError("Subclasses must implement run_test()")
    
    def execute(self):
        """
        Execute the tests with proper setup and teardown.
        """
        self.setup()
        
        try:
            # Use context managers as requested
            with self.tp20 as tp20:
                with self.kwp2000_client as kwp2000_client:
                    print("TP20 channel and KWP2000 client established successfully!\n")
                    
                    # Run the tests-specific logic
                    self.run_test()
                    
                    print("Test completed successfully!")
        finally:
            self.teardown()


def simulate_tester_base(csv_filename: str, dest: int = 0x01, test_logic=None):
    """
    Base function to simulate a tester sending and receiving CAN messages.
    
    Args:
        csv_filename: Path to the CSV file containing CAN messages (relative to calling file)
        dest: ECU logical address (default: 0x01)
        test_logic: Optional function to execute tests-specific logic.
                   Receives (tp20, kwp2000_client) as arguments.
    """
    # Get the CSV path relative to the calling tests file
    test_file_path = Path(sys._getframe(1).f_globals.get('__file__', ''))
    csv_path = test_file_path.parent / csv_filename
    
    # Initialize CSV-based CAN connection
    can_connection = MockupCan(str(csv_path))
    
    # Create TP20 transport layer
    tp20 = TP20Transport(
        can_connection=can_connection,
        dest=dest,
    )
    
    # Create KWP2000 client - TP20Transport can be used directly
    kwp2000_client = KWP2000Client(tp20)
    
    # Use context managers as requested
    with tp20 as tp20:
        with kwp2000_client as kwp2000_client:
            print("TP20 channel and KWP2000 client established successfully!\n")
            
            # Execute tests-specific logic if provided
            if test_logic:
                test_logic(tp20, kwp2000_client)
            
            print("Test completed successfully!")
