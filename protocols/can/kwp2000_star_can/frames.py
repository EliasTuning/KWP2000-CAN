"""Frame parsing and building for KWP2000-STAR protocol."""

from typing import Tuple

from .constants import TARGET_ADDR, SRC_ADDR
from .exceptions import InvalidFrameException


def build_frame(payload: bytes) -> bytes:
    """
    Build a complete KWP2000-STAR frame.
    
    KWP2000-STAR frame format:
    [TARGET_ADDR, length, payload...]
    
    Args:
        payload: Payload bytes
        
    Returns:
        Complete frame bytes
    """
    length = len(payload)
    
    # Build frame
    frame = bytes([TARGET_ADDR, length]) + payload
    
    return frame


def parse_frame(frame: bytes) -> Tuple[bytes]:
    """
    Parse a KWP2000-STAR frame.
    
    Frame format when receiving:
    [SRC_ADDR, length, payload...]
    
    Args:
        frame: Complete frame bytes
        
    Returns:
        Tuple containing (payload,)
        
    Raises:
        InvalidFrameException: If frame is invalid
    """
    if len(frame) < 2:
        raise InvalidFrameException(f"Frame too short: must be at least 2 bytes, got {len(frame)}")
    
    # Verify source address (first byte should be SRC_ADDR when receiving)
    if frame[0] != SRC_ADDR:
        raise InvalidFrameException(f"Invalid source address: expected {SRC_ADDR:02X}, got {frame[0]:02X}")
    
    # Extract length
    length = frame[1]
    
    # Verify frame length
    expected_frame_length = 1 + 1 + length  # SRC_ADDR + length + payload
    if len(frame) < expected_frame_length:
        raise InvalidFrameException(
            f"Frame too short: expected {expected_frame_length} bytes, got {len(frame)}"
        )
    
    # Extract payload
    payload = frame[2:2+length]
    
    return (payload,)
