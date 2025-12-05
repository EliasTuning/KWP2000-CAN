"""Exception classes for KWP2000 library."""

from kwp2000.constants import NEGATIVE_RESPONSE_CODES


class KWP2000Exception(Exception):
    """Base exception for all KWP2000 errors."""
    pass


class TimeoutException(KWP2000Exception):
    """Raised when a timeout occurs waiting for a response."""
    pass


class InvalidChecksumException(KWP2000Exception):
    """Raised when a frame has an invalid checksum."""
    pass


class InvalidFrameException(KWP2000Exception):
    """Raised when a frame cannot be parsed."""
    pass


class NegativeResponseException(KWP2000Exception):
    """Raised when a negative response is received."""
    def __init__(self, service_id, response_code, message=None):
        self.service_id = service_id
        self.response_code = response_code
        self.message = message
        
        # Get error description from codes dictionary
        error_description = NEGATIVE_RESPONSE_CODES.get(
            response_code, 
            f"Unknown error code {response_code:02X}"
        )
        
        error_msg = (
            f"Negative response: service={service_id:02X}, "
            f"code={response_code:02X} ({error_description})"
        )
        
        if message:
            error_msg = f"{error_msg}: {message}"
        
        super().__init__(error_msg)


class TransportException(KWP2000Exception):
    """Raised when a transport error occurs."""
    pass

