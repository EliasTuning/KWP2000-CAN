import csv
from dataclasses import dataclass
from typing import List, Optional, Tuple

from protocols.can.tp20 import TP20Exception

from interface.base_can_connection import CanConnection


@dataclass
class CanMessage:
    """Dataclass representing a CAN message from the CSV."""
    can_id: int
    data_bytes: bytes
    type: str
    description: str
    sender: str

    @classmethod
    def from_csv_row(cls, row: dict) -> 'CanMessage':
        """Create a CanMessage instance from a CSV row."""
        # Parse CAN ID (hex string)
        can_id = int(row['CAN ID'], 16)
        
        # Parse data bytes (hex string like "01 C0 00 10 00 03 01")
        hex_string = row['Data Bytes'].strip()
        if hex_string:
            # Remove spaces and convert hex string to bytes
            hex_clean = hex_string.replace(' ', '')
            data_bytes = bytes.fromhex(hex_clean)
        else:
            data_bytes = b''
        
        return cls(
            can_id=can_id,
            data_bytes=data_bytes,
            type=row['Type'],
            description=row['Description'],
            sender=row['Sender']
        )


class MockupCan(CanConnection):
    """
    Mock CAN interface that reads messages from CSV and simulates send/receive.
    
    Implements the CanConnection interface for use with TP20Transport.
    """
    
    def __init__(self, csv_filename: str):
        """
        Initialize MockupCan with messages from CSV file.
        
        Args:
            csv_filename: Path to the CSV file containing CAN messages
        """
        self.csv_filename = csv_filename
        self.messages: List[CanMessage] = []
        # Single stack of messages for both send and receive
        self.message_stack: List[CanMessage] = []
        self._is_open = False
        self._load_messages()
    
    def _load_messages(self):
        """Load CAN messages from CSV file."""
        try:
            with open(self.csv_filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip empty rows
                    if not row.get('CAN ID') or not row.get('CAN ID').strip():
                        continue
                    message = CanMessage.from_csv_row(row)
                    self.messages.append(message)
                    # Add to message stack (maintain order)
                    self.message_stack.append(message)
        except FileNotFoundError:
            raise TP20Exception(f"CSV file not found: {self.csv_filename}")
        except Exception as e:
            raise TP20Exception(f"Error loading CSV file: {e}")
    
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

