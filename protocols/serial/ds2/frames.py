"""Frame parsing and building for DS2 protocol."""

from typing import Tuple

from ds2.exceptions import InvalidChecksumException


def calculate_checksum(message: bytes) -> int:
    """
    Calculate XOR checksum for DS2 message.
    
    Args:
        message: Message bytes (address + size + payload)
        
    Returns:
        Checksum byte
    """
    result = 0
    for b in message:
        result ^= b
    return result


def build_frame(address: int, payload: bytes) -> bytes:
    """
    Build a complete DS2 frame.
    
    DS2 frame format:
    [address, size] + payload + checksum
    where size = 2 + len(payload) + 1 (address + size + payload + checksum)
    
    Args:
        address: Target address byte
        payload: Payload bytes
        
    Returns:
        Complete frame bytes
    """
    size = 2 + len(payload) + 1  # address + size + payload + checksum
    message = bytes([address, size]) + payload
    checksum = calculate_checksum(message)
    return message + bytes([checksum])


def parse_frame(frame: bytes) -> Tuple[int, bytes]:
    """
    Parse a DS2 frame.
    
    Args:
        frame: Complete frame bytes
        
    Returns:
        Tuple of (address, payload)
        
    Raises:
        ValueError: If frame is invalid
        InvalidChecksumException: If checksum is invalid
    """
    if len(frame) < 3:
        raise ValueError("Frame too short: must be at least 3 bytes")
    
    address = frame[0]
    size = frame[1]
    
    if size < 3:
        raise ValueError(f"Invalid size byte: {size}")
    
    if len(frame) < size:
        raise ValueError(f"Frame too short: expected {size} bytes, got {len(frame)}")
    
    # Extract payload (everything between size byte and checksum)
    payload = frame[2:size-1]
    
    # Verify checksum
    message = frame[:size-1]  # Everything except checksum
    expected_checksum = calculate_checksum(message)
    actual_checksum = frame[size-1]
    
    if actual_checksum != expected_checksum:
        raise InvalidChecksumException(
            f"Invalid checksum: expected {expected_checksum:02X}, got {actual_checksum:02X}"
        )
    
    return address, payload
