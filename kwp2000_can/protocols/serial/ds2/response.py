"""Response class for DS2."""

from typing import Optional

from .constants import (
    STATUS_OKAY,
    STATUS_BUSY,
    STATUS_ERROR_ECU_REJECTED,
    STATUS_ERROR_ECU_PARAMETER,
    STATUS_ERROR_ECU_FUNCTION,
    STATUS_ERROR_ECU_NUMBER,
    STATUS_ERROR_ECU_NACK,
)
from .exceptions import (
    InvalidChecksumException,
    ComputerBusy,
    InvalidParameter,
    InvalidCommand,
    ProtocolError,
)
from .frames import parse_frame


class Response:
    """
    Represents a DS2 response.
    
    Usage:
        frame = my_transport.wait_frame(timeout=1)
        response = Response.from_frame(frame, expected_address=IKE)
        if response.is_positive():
            print('Success!')
            data = response.data
    """
    
    def __init__(
        self,
        address: int,
        status: int,
        data: bytes = b''
    ):
        """
        Create a response.
        
        Args:
            address: Source address byte
            status: Status code byte
            data: Response data bytes (after status)
        """
        self.address = address
        self.status = status
        self.data = bytes(data)
    
    @classmethod
    def from_frame(cls, frame: bytes, expected_address: Optional[int] = None) -> 'Response':
        """
        Parse a response from frame bytes.
        
        Args:
            frame: Complete frame bytes
            expected_address: Optional expected source address for validation
            
        Returns:
            Response object
            
        Raises:
            InvalidChecksumException: If checksum is invalid
            ProtocolError: If unexpected sender
            ComputerBusy: If status is BUSY
            InvalidParameter: If status indicates invalid parameter
            InvalidCommand: If status indicates invalid command
        """
        try:
            address, payload = parse_frame(frame)
        except InvalidChecksumException:
            raise
        except Exception as e:
            raise ProtocolError(f"Failed to parse frame: {e}") from e
        
        if expected_address is not None and address != expected_address:
            raise ProtocolError(f"Unexpected sender: expected {expected_address:02X}, got {address:02X}")
        
        if len(payload) < 1:
            raise ProtocolError("Response payload too short: missing status byte")
        
        status = payload[0]
        data = payload[1:]
        
        # Check status and raise appropriate exceptions
        if status == STATUS_OKAY:
            return cls(address=address, status=status, data=data)
        elif status == STATUS_BUSY:
            raise ComputerBusy("Computer busy")
        elif status == STATUS_ERROR_ECU_REJECTED:
            raise ProtocolError("ECU rejected the request")
        elif status == STATUS_ERROR_ECU_PARAMETER:
            raise InvalidParameter("Invalid parameter")
        elif status == STATUS_ERROR_ECU_FUNCTION:
            raise ProtocolError("ECU function error")
        elif status == STATUS_ERROR_ECU_NUMBER:
            raise ProtocolError("ECU number error")
        elif status == STATUS_ERROR_ECU_NACK:
            raise InvalidCommand("Invalid command")
        else:
            # Unknown status - return response but log warning
            return cls(address=address, status=status, data=data)
    
    def is_positive(self) -> bool:
        """Check if response is positive (OKAY)."""
        return self.status == STATUS_OKAY
    
    def is_negative(self) -> bool:
        """Check if response is negative."""
        return self.status != STATUS_OKAY
    
    def __str__(self) -> str:
        """Return string representation of the response."""
        return f"Response(address={self.address:02X}, status={self.status:02X}, data={self.data.hex() if self.data else 'empty'})"
