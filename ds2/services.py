"""Service definitions for DS2."""

from typing import Optional
from dataclasses import dataclass
from ds2.request import Request
from ds2.response import Response
from ds2.constants import (
    CMD_READ_MEMORY,
    CMD_WRITE_MEMORY,
    MEMORY_TYPE_NAMES,
)


class ServiceBase:
    """Base class for services."""
    
    @classmethod
    def make_request(cls, *args, **kwargs) -> Request:
        """Create a request for this service."""
        raise NotImplementedError
    
    @classmethod
    def interpret_response(cls, response: Response):
        """Interpret a response for this service."""
        raise NotImplementedError


class ReadMemory(ServiceBase):
    """ReadMemory service (0x06)."""
    
    COMMAND_ID = CMD_READ_MEMORY
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_data: bytes
        memory_type_echo: int
        address_echo: int
        size_echo: int
    
    @classmethod
    def make_request(
        cls,
        address: int,
        memory_type: int,
        memory_address: int,
        memory_size: int = 1
    ) -> Request:
        """
        Create a ReadMemory request.
        
        Args:
            address: Target ECU address (e.g., IKE)
            memory_type: Memory type (0x01=ROM, 0x03=EEPROM, etc.)
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Number of bytes to read (default: 1)
            
        Returns:
            Request object
        """
        hex_str = format(cls.COMMAND_ID, '02x')
        hex_str += format(memory_type, '02x')
        # Address: 3 bytes, big-endian
        hex_str += memory_address.to_bytes(3, byteorder='big').hex()
        # Size
        hex_str += format(memory_size, '02x')
        payload = bytes.fromhex(hex_str)
        return Request(address=address, payload=payload)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadMemory.ServiceData':
        """
        Interpret a ReadMemory response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 5:
            raise ValueError("Invalid response data length: must be at least 5 bytes")
        
        memory_type_echo = response.data[0]
        address_high = response.data[1]
        address_middle = response.data[2]
        address_low = response.data[3]
        address_echo = (address_high << 16) | (address_middle << 8) | address_low
        size_echo = response.data[4]
        
        # Remaining bytes are memory data
        memory_data = response.data[5:]
        
        return cls.ServiceData(
            memory_data=memory_data,
            memory_type_echo=memory_type_echo,
            address_echo=address_echo,
            size_echo=size_echo
        )


class WriteMemory(ServiceBase):
    """WriteMemory service (0x07)."""
    
    COMMAND_ID = CMD_WRITE_MEMORY
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_type_echo: int
        address_echo: int
        size_echo: int
    
    @classmethod
    def make_request(
        cls,
        address: int,
        memory_type: int,
        memory_address: int,
        memory_content: bytes
    ) -> Request:
        """
        Create a WriteMemory request.
        
        Args:
            address: Target ECU address (e.g., IKE)
            memory_type: Memory type (0x01=ROM, 0x03=EEPROM, etc.)
            memory_address: Memory address (24-bit, 3 bytes)
            memory_content: Data bytes to write
            
        Returns:
            Request object
        """
        hex_str = format(cls.COMMAND_ID, '02x')
        hex_str += format(memory_type, '02x')
        # Address: 3 bytes, big-endian
        hex_str += memory_address.to_bytes(3, byteorder='big').hex()
        # Size
        memory_len = len(memory_content)
        hex_str += format(memory_len, '02x')
        hex_str += memory_content.hex()
        payload = bytes.fromhex(hex_str)
        return Request(address=address, payload=payload)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'WriteMemory.ServiceData':
        """
        Interpret a WriteMemory response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 5:
            raise ValueError("Invalid response data length: must be at least 5 bytes")
        
        memory_type_echo = response.data[0]
        address_high = response.data[1]
        address_middle = response.data[2]
        address_low = response.data[3]
        address_echo = (address_high << 16) | (address_middle << 8) | address_low
        size_echo = response.data[4]
        
        return cls.ServiceData(
            memory_type_echo=memory_type_echo,
            address_echo=address_echo,
            size_echo=size_echo
        )


class Ident(ServiceBase):
    """Ident service (0x04)."""
    
    COMMAND_ID = 0x04
    
    @classmethod
    def make_request(
        cls,
        address: int
    ) -> Request:
        """
        Create an Ident request.
        
        Args:
            address: Target ECU address (e.g., MOTRONIC)
            
        Returns:
            Request object
        """
        payload = bytes([cls.COMMAND_ID, 0x00])
        return Request(address=address, payload=payload)
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret an Ident response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data containing identification information
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) > 0:
            result['data'] = response.data
        
        return result


def get_memory_type_by_name(name: str) -> int:
    """
    Get memory type by name.
    
    Args:
        name: Memory type name ('eeprom', 'rom', 'dpram', 'internalram', 'externalram')
        
    Returns:
        Memory type byte
        
    Raises:
        ValueError: If name is not recognized
    """
    if name.lower() not in MEMORY_TYPE_NAMES:
        raise ValueError(f"Unknown memory type: {name}")
    return MEMORY_TYPE_NAMES[name.lower()]
