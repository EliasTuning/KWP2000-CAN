from typing import List, Optional, Tuple, Callable, Union

from protocols.can.tp20 import TP20Exception

from interface.base_can_connection import CanConnection

# Import CanMessage and parsers from message_parsers module
try:
    from .message_parsers import CanMessage, parse_csv_messages
except ImportError:
    # Fallback for direct import
    from message_parsers import CanMessage, parse_csv_messages


class MockupCan(CanConnection):
    """
    Mock CAN interface that reads messages from a parser function and simulates send/receive.
    
    Implements the CanConnection interface for use with TP20Transport and other CAN protocols.
    
    The parser function should return a list of CanMessage instances in the order they should
    be processed (both sent and received).
    """
    
    def __init__(self, parser: Union[Callable[[], List[CanMessage]], str]):
        """
        Initialize MockupCan with messages from a parser function or CSV filename.
        
        Args:
            parser: Either:
                - A callable that returns List[CanMessage] (e.g., lambda: parse_csv_messages('file.csv'))
                - A string filename (for backward compatibility, treated as CSV filename)
        """
        self.parser = parser
        self.messages: List[CanMessage] = []
        # Single stack of messages for both send and receive
        self.message_stack: List[CanMessage] = []
        self._is_open = False
        self._load_messages()
    
    def _load_messages(self):
        """Load CAN messages using the parser function."""
        try:
            # Backward compatibility: if parser is a string, treat it as CSV filename
            if isinstance(self.parser, str):
                messages = parse_csv_messages(self.parser)
            else:
                # Parser is a callable
                messages = self.parser()
            
            self.messages = messages
            # Add to message stack (maintain order)
            self.message_stack = messages.copy()
        except FileNotFoundError as e:
            raise TP20Exception(f"File not found: {e}")
        except Exception as e:
            raise TP20Exception(f"Error loading messages: {e}")
    
    def open(self) -> None:
        """Open the CAN connection and reload messages."""
        self._is_open = True
    
    def close(self) -> None:
        """Close the CAN connection."""
        self._is_open = False
    
    def send_can_frame(self, can_id: int, data: bytes) -> None:
        """
        Send a CAN frame (simulated - verifies against CSV expectations).
        
        Implements CanConnection interface for TP20Transport.
        
        Args:
            can_id: CAN ID (11-bit or 29-bit)
            data: Data payload (up to 8 bytes)
            
        Raises:
            TP20Exception: If connection not open, data too long, or message doesn't match CSV
        """
        if not self._is_open:
            raise TP20Exception("CAN connection not open")
        if len(data) > 8:
            raise TP20Exception(f"CAN frame data too long: {len(data)} bytes (max 8)")
        
        # Check if there are any messages in the stack
        if not self.message_stack:
            raise TP20Exception("No expected message available")
        if data[0] == 0xA3:
            return
        
        # Pop the next message from the stack
        expected_msg = self.message_stack.pop(0)
        
        # Check if the sender type is correct
        if expected_msg.sender.lower() != 'tester':
            raise TP20Exception(
                f"Wrong sender type: expected 'tester', got '{expected_msg.sender}'"
            )
        
        # Verify the message matches
        if expected_msg.can_id != can_id:
            raise TP20Exception(
                f"CAN ID mismatch: expected 0x{expected_msg.can_id:03X}, got 0x{can_id:03X}"
            )
        
        if expected_msg.data_bytes != data:
            raise TP20Exception(
                f"Data mismatch for CAN ID 0x{can_id:03X}: "
                f"expected {expected_msg.data_bytes.hex(' ').upper()}, got {data.hex(' ').upper()}"
            )
        
        print(f"[SEND] CAN ID: 0x{can_id:03X}, Data: {data.hex(' ').upper()}")
        if expected_msg.description:
            print(f"         Description: {expected_msg.description}")
    
    def recv_can_frame(self, timeout: float = 1.0) -> Optional[Tuple[int, bytes]]:
        """
        Receive a CAN frame (simulated - returns next ECU message from CSV).
        
        Implements CanConnection interface for TP20Transport.
        
        Args:
            timeout: Maximum time to wait in seconds (ignored in CSV mode)
            
        Returns:
            Tuple of (can_id, data), or None if no ECU message available
            
        Raises:
            TP20Exception: If connection not open
        """
        if not self._is_open:
            raise TP20Exception("CAN connection not open")
        
        # Check if there are any messages in the stack
        if not self.message_stack:
            return None
        
        # Peek at the next message without popping it
        msg = self.message_stack[0]
        
        # Only return (and pop) if it's an ECU message
        # This prevents the worker thread from consuming tester messages
        if msg.sender.lower() != 'ecu':
            return None
        
        # Pop the message now that we know it's an ECU message
        msg = self.message_stack.pop(0)
        
        print(f"[RECEIVE] CAN ID: 0x{msg.can_id:03X}, Data: {msg.data_bytes.hex(' ').upper()}")
        print(f"         Type: {msg.type}, Description: {msg.description}")
        return (msg.can_id, msg.data_bytes)
    
    def get_messages_by_sender(self, sender: str) -> List[CanMessage]:
        """Get all messages from a specific sender."""
        return [msg for msg in self.messages if msg.sender.lower() == sender.lower()]
    
    def get_messages_by_type(self, msg_type: str) -> List[CanMessage]:
        """Get all messages of a specific type."""
        return [msg for msg in self.messages if msg.type.lower() == msg_type.lower()]

