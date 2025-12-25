"""Exception classes for KWP2000-STAR library."""


class KWP2000StarException(Exception):
    """Base exception for all KWP2000-STAR errors."""
    pass


class ProtocolError(KWP2000StarException):
    """Raised when a protocol error occurs."""
    pass


class InvalidChecksumException(KWP2000StarException):
    """Raised when a frame has an invalid checksum."""
    pass


class InvalidFrameException(KWP2000StarException):
    """Raised when a frame is invalid."""
    pass
