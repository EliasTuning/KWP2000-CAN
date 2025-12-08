"""Exception classes for DS2 library."""


class DS2Exception(Exception):
    """Base exception for all DS2 errors."""
    pass


class ProtocolError(DS2Exception):
    """Raised when a protocol error occurs."""
    pass


class ComputerBusy(DS2Exception):
    """Raised when the computer is busy."""
    pass


class InvalidAddress(DS2Exception):
    """Raised when an invalid address is used."""
    pass


class InvalidCommand(DS2Exception):
    """Raised when an invalid command is sent."""
    pass


class InvalidParameter(DS2Exception):
    """Raised when an invalid parameter is provided."""
    pass


class TimeoutException(DS2Exception):
    """Raised when a timeout occurs waiting for a response."""
    pass


class InvalidChecksumException(DS2Exception):
    """Raised when a frame has an invalid checksum."""
    pass


class TransportException(DS2Exception):
    """Raised when a transport error occurs."""
    pass
