"""Frame parsing and building for KWP2000 protocol."""

from typing import Optional, Tuple
from kwp2000.constants import (
    ADDRESS_MODE_NO_ADDRESS,
    ADDRESS_MODE_EXCEPTION,
    ADDRESS_MODE_PHYSICAL,
    ADDRESS_MODE_FUNCTIONAL,
    LENGTH_MASK,
    ADDRESS_MODE_MASK,
)


def parse_format_byte(fmt_byte: int) -> Tuple[int, int]:
    """
    Parse format byte into address mode and length.
    
    Args:
        fmt_byte: Format byte value
        
    Returns:
        Tuple of (address_mode, length)
        - address_mode: 0=no address, 1=exception, 2=physical, 3=functional
        - length: Length in format byte (0 if extended length byte used)
    """
    address_mode = (fmt_byte & ADDRESS_MODE_MASK) >> 6
    length = fmt_byte & LENGTH_MASK
    return address_mode, length


def build_format_byte(address_mode: int, length: int) -> int:
    """
    Build format byte from address mode and length.
    
    Args:
        address_mode: 0=no address, 1=exception, 2=physical, 3=functional
        length: Length (0-63, or 0 if using extended length byte)
        
    Returns:
        Format byte value
    """
    if length > 63:
        length = 0  # Must use extended length byte
    return ((address_mode & 0x03) << 6) | (length & LENGTH_MASK)


def build_frame(
    service_id: int,
    data: bytes = b'',
    target_address: Optional[int] = None,
    source_address: Optional[int] = None,
    use_extended_length: bool = False
) -> bytes:
    """
    Build a complete KWP2000 frame.
    
    Args:
        service_id: Service ID byte
        data: Additional data bytes (after service ID)
        target_address: Optional target address byte
        source_address: Optional source address byte
        use_extended_length: If True, always use extended length byte
        
    Returns:
        Complete frame bytes
    """
    # Determine address mode
    if target_address is not None and source_address is not None:
        address_mode = ADDRESS_MODE_PHYSICAL  # Could be functional, but physical is default
    else:
        address_mode = ADDRESS_MODE_NO_ADDRESS
    
    # Calculate data length (service ID + data bytes)
    data_length = 1 + len(data)  # Service ID + data
    
    # Build header
    header = bytearray()
    
    # Format byte
    if use_extended_length or data_length >= 64:
        fmt_byte = build_format_byte(address_mode, 0)
        header.append(fmt_byte)
        
        # Add address bytes if present
        if target_address is not None:
            header.append(target_address)
        if source_address is not None:
            header.append(source_address)
        
        # Extended length byte
        header.append(data_length)
    else:
        fmt_byte = build_format_byte(address_mode, data_length)
        header.append(fmt_byte)
        
        # Add address bytes if present
        if target_address is not None:
            header.append(target_address)
        if source_address is not None:
            header.append(source_address)
    
    # Build complete message (header + data)
    message = bytes(header) + bytes([service_id]) + data
    
    return message


def parse_frame(frame: bytes) -> Tuple[int, bytes, Optional[int], Optional[int]]:
    """
    Parse a KWP2000 frame.
    
    Args:
        frame: Complete frame bytes
        
    Returns:
        Tuple of (service_id, data_bytes, target_address, source_address)
        target_address and source_address are None if not present
    """
    if len(frame) < 2:
        raise ValueError("Frame too short")
    
    # Parse format byte
    fmt_byte = frame[0]
    address_mode, length = parse_format_byte(fmt_byte)
    
    # Determine header length
    header_start = 1
    if address_mode == ADDRESS_MODE_PHYSICAL or address_mode == ADDRESS_MODE_FUNCTIONAL:
        header_start = 3  # Format + Target + Source
    elif address_mode == ADDRESS_MODE_EXCEPTION:
        header_start = 3  # Format + Target + Source (CARB mode)
    else:
        header_start = 1  # Format only
    
    # Check if extended length byte is used
    if length == 0:
        if header_start >= len(frame):
            raise ValueError("Frame too short for extended length")
        data_length = frame[header_start]
        header_start += 1
    else:
        data_length = length
    
    # Extract addresses
    target_address = None
    source_address = None
    if address_mode == ADDRESS_MODE_PHYSICAL or address_mode == ADDRESS_MODE_FUNCTIONAL:
        if len(frame) < 3:
            raise ValueError("Frame too short for address bytes")
        target_address = frame[1]
        source_address = frame[2]
    
    # Extract service ID and data
    data_start = header_start
    if data_start >= len(frame):
        raise ValueError("Frame too short for service ID")
    
    service_id = frame[data_start]
    data_end = data_start + data_length
    
    if data_end > len(frame):
        raise ValueError("Frame length mismatch")
    
    data_bytes = frame[data_start + 1:data_end]
    
    return service_id, data_bytes, target_address, source_address

