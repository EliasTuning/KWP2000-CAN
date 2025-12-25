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

# Lazy import for can module to avoid circular imports
# KWP2000_TP20_J2534 will be imported on-demand
_can_module = None
_KWP2000_TP20_J2534 = None

def __getattr__(name):
    """Lazy import for can module to avoid circular imports."""
    if name == "KWP2000_TP20_J2534":
        global _KWP2000_TP20_J2534
        if _KWP2000_TP20_J2534 is None:
            from .can import KWP2000_TP20_J2534
            _KWP2000_TP20_J2534 = KWP2000_TP20_J2534
        return _KWP2000_TP20_J2534
    if name == "can":
        global _can_module
        if _can_module is None:
            from . import can
            _can_module = can
        return _can_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
    # Convenience wrappers
    "KWP2000_TP20_J2534",
    # Modules
    "can",
    "services",
]

