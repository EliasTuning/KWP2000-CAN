"""Frame parsing and building for KWP2000-STAR protocol."""

from typing import Tuple
from .exceptions import InvalidChecksumException, InvalidFrameException
from .constants import START_BYTE, TARGET_ADDR, SRC_ADDR


def calculate_checksum(message: bytes) -> int:
    """
    Calculate XOR checksum for KWP2000-STAR message.
    
    Same checksum calculation as DS2 protocol (XOR of all bytes).
    
    Args:
        message: Message bytes (start_byte + target_addr + src_addr + len + payload)
        
    Returns:
        Checksum byte
    """
    result = 0
    for b in message:
        result ^= b
    return result


def build_frame(payload: bytes) -> bytes:
    """
    Build a complete KWP2000-STAR frame.
    
    KWP2000-STAR frame format:
    [START_BYTE, TARGET_ADDR, SRC_ADDR, len, payload..., checksum]
    
    Checksum is calculated on: [START_BYTE, TARGET_ADDR, SRC_ADDR, len, payload...]
    
    Args:
        payload: Payload bytes
        
    Returns:
        Complete frame bytes
    """
    length = len(payload)
    
    # Build message for checksum calculation (everything except checksum)
    message = bytes([START_BYTE, TARGET_ADDR, SRC_ADDR, length]) + payload
    
    # Calculate checksum
    checksum = calculate_checksum(message)
    
    # Build complete frame
    frame = message + bytes([checksum])
    
    return frame


def parse_frame(frame: bytes) -> Tuple[bytes]:
    """
    Parse a KWP2000-STAR frame.
    
    Args:
        frame: Complete frame bytes
        
    Returns:
        Tuple containing (payload,)
        
    Raises:
        InvalidFrameException: If frame is invalid
        InvalidChecksumException: If checksum is invalid
    """
    if len(frame) < 5:
        raise InvalidFrameException(f"Frame too short: must be at least 5 bytes, got {len(frame)}")
    
    # Verify start byte
    if frame[0] != START_BYTE:
        raise InvalidFrameException(f"Invalid start byte: expected {START_BYTE:02X}, got {frame[0]:02X}")
    
    # Verify target address
    if frame[1] != TARGET_ADDR:
        #raise InvalidFrameException(f"Invalid target address: expected {TARGET_ADDR:02X}, got {frame[1]:02X}")
        pass
    
    # Verify source address
    if frame[2] != SRC_ADDR:
        #raise InvalidFrameException(f"Invalid source address: expected {SRC_ADDR:02X}, got {frame[2]:02X}")
        pass
    #print(frame.hex())

    # Extract length
    length = frame[3]
    
    # Verify frame length
    expected_frame_length = 1 + 3 + length + 1  # START_BYTE + TARGET_ADDR + SRC_ADDR + len + payload + checksum
    if len(frame) < expected_frame_length:
        raise InvalidFrameException(
            f"Frame too short: expected {expected_frame_length} bytes, got {len(frame)}"
        )
        pass
    
    # Extract payload
    payload = frame[4:4+length]
    
    # Verify checksum (everything except checksum itself)
    message = frame[0:4+length]  # START_BYTE + TARGET_ADDR + SRC_ADDR + len + payload
    expected_checksum = calculate_checksum(message)
    actual_checksum = frame[4+length]
    
    if actual_checksum != expected_checksum:
        raise InvalidChecksumException(
            f"Invalid checksum: expected {expected_checksum:02X}, got {actual_checksum:02X}"
        )
    
    return (payload,)
