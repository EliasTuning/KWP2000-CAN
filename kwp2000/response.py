"""Response class for KWP2000."""

from typing import Optional
from kwp2000.frames import parse_frame
from kwp2000.constants import RESPONSE_POSITIVE, RESPONSE_NEGATIVE
from kwp2000.exceptions import InvalidFrameException, NegativeResponseException


class Response:
    """
    Represents a KWP2000 response.
    
    Usage:
        payload = my_connection.wait_frame(timeout=1)
        response = Response.from_payload(payload)
        if response.code == Response.Code.PositiveResponse:
            print('Success!')
    """
    
    class Code:
        """Response code constants."""
        PositiveResponse = "PositiveResponse"
        NegativeResponse = "NegativeResponse"
    
    def __init__(
        self,
        service: int,
        code: str,
        data: bytes = b'',
        target_address: Optional[int] = None,
        source_address: Optional[int] = None
    ):
        """
        Create a response.
        
        Args:
            service: Service ID
            code: Response code (Response.Code.PositiveResponse or NegativeResponse)
            data: Response data bytes
            target_address: Optional target address
            source_address: Optional source address
        """
        self.service = service
        self.code = code
        self.data = data
        self.target_address = target_address
        self.source_address = source_address
    
    @classmethod
    def from_payload(cls, payload: bytes) -> 'Response':
        """
        Parse a response from frame payload.
        
        Args:
            payload: Complete frame bytes
            
        Returns:
            Response object
            
        Raises:
            InvalidFrameException: If frame cannot be parsed
            NegativeResponseException: If negative response received
        """
        if payload is None or len(payload) < 1:
            raise InvalidFrameException("Invalid payload")
        
        # Check if this is raw service data (from TP20) or a full KWP2000 frame
        # Format bytes are typically 0x00-0x3F (address mode + length)
        # Service IDs are typically 0x10-0x3F (requests) or 0x40-0x7F (positive responses) or 0x7F (negative)
        # If first byte looks like a service ID (>= 0x10), treat as raw service data
        is_raw_service_data = len(payload) >= 1 and payload[0] >= 0x10
        
        if is_raw_service_data:
            # Raw service data: service_id + data_bytes
            service_id = payload[0]
            data_bytes = payload[1:]
            target_addr = None
            source_addr = None
        else:
            # Full KWP2000 frame: parse it
            try:
                service_id, data_bytes, target_addr, source_addr = parse_frame(payload)
            except ValueError as e:
                raise InvalidFrameException(f"Frame parse error: {e}")
        
        # Determine response type
        if service_id == RESPONSE_NEGATIVE:
            # Negative response: data_bytes[0] is requested service, data_bytes[1] is response code
            if len(data_bytes) < 2:
                raise InvalidFrameException("Invalid negative response format")
            requested_service = data_bytes[0]
            response_code = data_bytes[1]
            raise NegativeResponseException(
                requested_service,
                response_code,
                f"Negative response: service={requested_service:02X}, code={response_code:02X}"
            )
        elif service_id >= RESPONSE_POSITIVE and service_id < 0x80:
            # Positive response: service_id is request_service + 0x40
            request_service = service_id - RESPONSE_POSITIVE
            return cls(
                service=request_service,
                code=cls.Code.PositiveResponse,
                data=data_bytes,
                target_address=target_addr,
                source_address=source_addr
            )
        else:
            # Communication service response (e.g., StartCommunication = 0xC1, StopCommunication = 0xC2)
            # These are positive responses but don't follow the +0x40 pattern
            return cls(
                service=service_id,
                code=cls.Code.PositiveResponse,
                data=data_bytes,
                target_address=target_addr,
                source_address=source_addr
            )
    
    def is_positive(self) -> bool:
        """Check if response is positive."""
        return self.code == self.Code.PositiveResponse
    
    def is_negative(self) -> bool:
        """Check if response is negative."""
        return self.code == self.Code.NegativeResponse
    
    def __str__(self) -> str:
        """Return string representation of the response."""
        parts = [
            f"Response(code={self.code}",
            f"service={self.service:02X}",
            f"data={self.data.hex() if self.data else 'empty'}"
        ]
        if self.target_address is not None:
            parts.append(f"target={self.target_address:02X}")
        if self.source_address is not None:
            parts.append(f"source={self.source_address:02X}")
        return ", ".join(parts) + ")"
