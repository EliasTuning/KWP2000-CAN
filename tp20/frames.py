"""Frame building and parsing for TP20 protocol."""

from typing import Optional, Tuple
from tp20.constants import (
    OPCODE_SETUP_REQUEST,
    OPCODE_SETUP_POSITIVE_RESPONSE,
    OPCODE_SETUP_NEGATIVE_RESPONSE_MIN,
    OPCODE_SETUP_NEGATIVE_RESPONSE_MAX,
    OPCODE_PARAMETERS_REQUEST,
    OPCODE_PARAMETERS_RESPONSE,
    OPCODE_CHANNEL_TEST,
    OPCODE_BREAK,
    OPCODE_DISCONNECT,
    DATA_OP_MASK,
    SEQ_MASK,
    APP_TYPE_KWP,
)


def build_setup_request(
    dest: int,
    rx_id: int = 0x300,
    tx_id: int = 0x300,
    rx_valid: bool = False,
    tx_valid: bool = True,
    app_type: int = APP_TYPE_KWP
) -> bytes:
    """
    Build a channel setup request frame.
    
    Args:
        dest: Logical address of destination module (e.g., 0x01 for ECU)
        rx_id: CAN ID for destination module to listen to (lower byte)
        tx_id: CAN ID for destination module to transmit from (lower byte)
        rx_valid: Whether RX ID is valid (0x0=valid, 0x1=invalid)
        tx_valid: Whether TX ID is valid (0x0=valid, 0x1=invalid)
        app_type: Application type (default: 0x01 for KWP)
        
    Returns:
        7-byte setup request frame
    """
    rx_prefix = (rx_id >> 8) & 0xFF
    rx_low = rx_id & 0xFF
    tx_prefix = (tx_id >> 8) & 0xFF
    tx_low = tx_id & 0xFF
    
    rx_v = 0x1 if rx_valid else 0x0
    tx_v = 0x1 if tx_valid else 0x0
    
    return bytes([
        dest,
        OPCODE_SETUP_REQUEST,
        rx_low,
        (rx_v << 4) | (rx_prefix & 0x0F),
        tx_low,
        (tx_v << 4) | (tx_prefix & 0x0F),
        app_type
    ])


def parse_setup_response(data: bytes) -> Tuple[int, int, int, bool, bool, int]:
    """
    Parse a channel setup response frame.
    
    Args:
        data: 7-byte setup response frame
        
    Returns:
        Tuple of (dest, rx_id, tx_id, rx_valid, tx_valid, app_type)
    """
    if len(data) != 7:
        raise ValueError(f"Invalid setup response length: {len(data)} (expected 7)")
    
    dest = data[0]
    opcode = data[1]
    
    if opcode == OPCODE_SETUP_POSITIVE_RESPONSE:
        rx_low = data[2]
        rx_byte = data[3]
        rx_valid = (rx_byte >> 4) & 0x01 == 0x0
        rx_prefix = rx_byte & 0x0F
        rx_id = (rx_prefix << 8) | rx_low
        
        tx_low = data[4]
        tx_byte = data[5]
        tx_valid = (tx_byte >> 4) & 0x01 == 0x0
        tx_prefix = tx_byte & 0x0F
        tx_id = (tx_prefix << 8) | tx_low
        
        app_type = data[6]
        
        return dest, rx_id, tx_id, rx_valid, tx_valid, app_type
    elif OPCODE_SETUP_NEGATIVE_RESPONSE_MIN <= opcode <= OPCODE_SETUP_NEGATIVE_RESPONSE_MAX:
        raise ValueError(f"Negative setup response: opcode={opcode:02X}")
    else:
        raise ValueError(f"Invalid setup response opcode: {opcode:02X}")


def build_parameters_request(
    block_size: int = 0x0F,
    t1: int = 0x8A,
    t2: int = 0xFF,
    t3: int = 0x32,
    t4: int = 0xFF
) -> bytes:
    """
    Build a channel parameters request frame.
    
    Args:
        block_size: Block size (number of packets before ACK)
        t1: Timing parameter 1
        t2: Timing parameter 2 (usually 0xFF)
        t3: Timing parameter 3 (interval between packets)
        t4: Timing parameter 4 (usually 0xFF)
        
    Returns:
        6-byte parameters request frame
    """
    return bytes([
        OPCODE_PARAMETERS_REQUEST,
        block_size,
        t1,
        t2,
        t3,
        t4
    ])


def parse_parameters_response(data: bytes) -> Tuple[int, int, int, int, int]:
    """
    Parse a channel parameters response frame.
    
    Args:
        data: 6-byte parameters response frame
        
    Returns:
        Tuple of (block_size, t1, t2, t3, t4)
    """
    if len(data) != 6:
        raise ValueError(f"Invalid parameters response length: {len(data)} (expected 6)")
    
    if data[0] != OPCODE_PARAMETERS_RESPONSE:
        raise ValueError(f"Invalid parameters response opcode: {data[0]:02X}")
    
    return data[1], data[2], data[3], data[4], data[5]


def build_data_frame(opcode: int, sequence: int, payload: bytes) -> bytes:
    """
    Build a TP20 data transmission frame.
    
    Args:
        opcode: Data opcode (upper 4 bits: 0x0, 0x1, 0x2, 0x3, 0x9, 0xB)
        sequence: Sequence number (lower 4 bits: 0x0-0xF)
        payload: Payload data (up to 7 bytes for first byte with opcode+seq)
        
    Returns:
        Data frame bytes (1-8 bytes)
    """
    if opcode > 0xF or sequence > 0xF:
        raise ValueError("Opcode and sequence must be 4-bit values")
    
    first_byte = (opcode << 4) | (sequence & SEQ_MASK)
    
    frame = bytearray([first_byte])
    frame.extend(payload[:7])  # Max 7 bytes after first byte
    
    return bytes(frame)


def parse_data_frame(data: bytes) -> Tuple[int, int, bytes]:
    """
    Parse a TP20 data transmission frame.
    
    Args:
        data: Data frame bytes
        
    Returns:
        Tuple of (opcode, sequence, payload)
    """
    if len(data) < 1:
        raise ValueError("Data frame too short")
    
    first_byte = data[0]
    opcode = (first_byte & DATA_OP_MASK) >> 4
    sequence = first_byte & SEQ_MASK
    payload = data[1:]
    
    return opcode, sequence, payload


def build_disconnect() -> bytes:
    """Build a disconnect frame."""
    return bytes([OPCODE_DISCONNECT])


def build_channel_test() -> bytes:
    """Build a channel test (keep-alive) frame."""
    return bytes([OPCODE_CHANNEL_TEST])


def build_break() -> bytes:
    """Build a break frame."""
    return bytes([OPCODE_BREAK])

