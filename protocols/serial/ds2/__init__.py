"""
DS2 Python Library

A Python library for DS2 (Diagnostic System 2) communication,
similar in API design to KWP2000.
"""

from .client import DS2Client
from .request import Request
from .response import Response
from .transport import Transport, MockTransport
from . import services, exceptions
from .constants import (
    MOTRONIC,
    AUTOMATIC_TRANSMISSION,
    IKE,
    LCM,
    CMD_SET_ANALOG,
    CMD_READ_MEMORY,
    CMD_WRITE_MEMORY,
    CMD_ACTIVATE_TEST,
    CMD_DEACTIVATE_TEST,
    MEMORY_TYPE_ROM,
    MEMORY_TYPE_EEPROM,
    MEMORY_TYPE_INTERNAL_RAM,
    MEMORY_TYPE_EXTERNAL_RAM,
    MEMORY_TYPE_DPRAM,
)

__version__ = "0.1.0"

# Backward compatibility alias
Client = DS2Client

__all__ = [
    'DS2Client',
    'Client',  # Backward compatibility
    'Transport',
    'MockTransport',
    'Request',
    'Response',
    'services',
    'exceptions',
    'MOTRONIC',
    'AUTOMATIC_TRANSMISSION',
    'IKE',
    'LCM',
    'CMD_SET_ANALOG',
    'CMD_READ_MEMORY',
    'CMD_WRITE_MEMORY',
    'CMD_ACTIVATE_TEST',
    'CMD_DEACTIVATE_TEST',
    'MEMORY_TYPE_ROM',
    'MEMORY_TYPE_EEPROM',
    'MEMORY_TYPE_INTERNAL_RAM',
    'MEMORY_TYPE_EXTERNAL_RAM',
    'MEMORY_TYPE_DPRAM',
]

# Optional import for COM port support (may fail if pyserial not available)
try:
    from .comport_transport import ComportTransport
    __all__.append('ComportTransport')
except ImportError:
    pass  # pyserial not available
