"""Message parsers for different CAN message formats."""

import csv
from dataclasses import dataclass
from typing import List, Callable, Optional
from pathlib import Path


@dataclass
class CanMessage:
    """Dataclass representing a CAN message."""
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

    @classmethod
    def from_candump_line(cls, line: str, tx_id: int, rx_id: int) -> Optional['CanMessage']:
        """
        Create a CanMessage instance from a candump format line.
        
        Format: can0  6F1   [8]  12 02 1A 80 00 00 00 00
        Format: interface  can_id  [length]  data_bytes
        
        Args:
            line: Line from candump file
            tx_id: CAN ID used for tester transmissions (determines sender='tester')
            rx_id: CAN ID used for ECU transmissions (determines sender='ecu')
            
        Returns:
            CanMessage instance or None if line is invalid/empty
        """
        # Strip whitespace
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return None
        
        # Skip comment lines
        if line.startswith('#'):
            return None
        
        # Split by whitespace
        parts = line.split()
        
        # Need at least: interface, can_id, [length], and some data
        if len(parts) < 4:
            return None
        
        # Parse CAN ID (hex, no 0x prefix)
        try:
            can_id = int(parts[1], 16)
        except (ValueError, IndexError):
            return None
        
        # Determine sender based on CAN ID
        if can_id == tx_id:
            sender = 'tester'
        elif can_id == rx_id:
            sender = 'ecu'
        else:
            # Unknown sender, skip or mark as unknown
            sender = 'unknown'
        
        # Parse length (in brackets)
        try:
            length_str = parts[2].strip('[]')
            length = int(length_str)
        except (ValueError, IndexError):
            return None
        
        # Parse data bytes (everything after [length])
        hex_parts = parts[3:]
        hex_string = ' '.join(hex_parts)
        
        # Convert hex string to bytes
        try:
            hex_clean = hex_string.replace(' ', '')
            data_bytes = bytes.fromhex(hex_clean)
            
            # Truncate to specified length if needed
            if len(data_bytes) > length:
                data_bytes = data_bytes[:length]
            # Pad to length if needed (though this shouldn't happen)
            elif len(data_bytes) < length:
                data_bytes = data_bytes.ljust(length, b'\x00')
        except ValueError:
            return None
        
        return cls(
            can_id=can_id,
            data_bytes=data_bytes,
            type='Data',  # Default type for candump format
            description=f'CAN message from {sender}',  # Default description
            sender=sender
        )


def parse_csv_messages(csv_filename: str) -> List[CanMessage]:
    """
    Parse CAN messages from a CSV file.
    
    Args:
        csv_filename: Path to CSV file
        
    Returns:
        List of CanMessage instances
        
    Raises:
        FileNotFoundError: If CSV file not found
        Exception: If parsing fails
    """
    messages = []
    try:
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row.get('CAN ID') or not row.get('CAN ID').strip():
                    continue
                message = CanMessage.from_csv_row(row)
                messages.append(message)
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_filename}")
    except Exception as e:
        raise Exception(f"Error loading CSV file: {e}")
    
    return messages


def parse_candump_messages(candump_filename: str, tx_id: int, rx_id: int) -> List[CanMessage]:
    """
    Parse CAN messages from a candump format file.
    
    Args:
        candump_filename: Path to candump format file
        tx_id: CAN ID used for tester transmissions
        rx_id: CAN ID used for ECU transmissions
        
    Returns:
        List of CanMessage instances
        
    Raises:
        FileNotFoundError: If file not found
        Exception: If parsing fails
    """
    messages = []
    try:
        with open(candump_filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                message = CanMessage.from_candump_line(line, tx_id, rx_id)
                if message is not None:
                    messages.append(message)
    except FileNotFoundError:
        raise FileNotFoundError(f"Candump file not found: {candump_filename}")
    except Exception as e:
        raise Exception(f"Error loading candump file: {e}")
    
    return messages

