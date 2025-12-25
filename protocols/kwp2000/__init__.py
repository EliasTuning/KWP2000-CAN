"""KWP2000 protocol implementation."""

from .constants import TimingParameters, TIMING_PARAMETER_STANDARD, TIMING_PARAMETER_MINIMAL
from .transport import Transport
from .exceptions import (
    KWP2000Exception,
    TimeoutException,
    InvalidChecksumException,
    InvalidFrameException,
    NegativeResponseException,
    TransportException,
)
from .client import KWP2000Client
from . import services

# Note: 'can' module and 'KWP2000_TP20_J2534' are not imported here to avoid circular imports.
# Import them directly: from protocols.kwp2000.can import KWP2000_TP20_J2534

__all__ = [
    # Timing parameters
    "TimingParameters",
    "TIMING_PARAMETER_STANDARD",
    "TIMING_PARAMETER_MINIMAL",
    # Transport
    "Transport",
    # Exceptions
    "KWP2000Exception",
    "TimeoutException",
    "InvalidChecksumException",
    "InvalidFrameException",
    "NegativeResponseException",
    "TransportException",
    # Client
    "KWP2000Client",
    # Modules
    "services",
]

