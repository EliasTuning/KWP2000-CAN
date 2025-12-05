"""
KWP2000 Python Library

A Python library for KWP2000 (Keyword Protocol 2000) communication,
similar in API design to udsoncan.
"""

from kwp2000.client import KWP2000Client
from kwp2000.transport import Transport, MockTransport
from kwp2000.request import Request
from kwp2000.response import Response
from kwp2000 import services
from kwp2000 import exceptions

__version__ = "0.1.0"

# Backward compatibility alias
Client = KWP2000Client

__all__ = [
    'KWP2000Client',
    'Client',  # Backward compatibility
    'Transport',
    'MockTransport',
    'Request',
    'Response',
    'services',
    'exceptions',
]

# Optional convenience wrapper for J2534+TP20+KWP2000
try:
    from kwp2000.can import KWP2000_TP20_J2534
    __all__.append('KWP2000_TP20_J2534')
except ImportError:
    pass  # J2534/TP20 dependencies not available

# Optional import for J2534 support (may fail if j2534 package not available)
try:
    from kwp2000.j2534_tp20 import J2534TP20Client
    __all__.append('J2534TP20Client')
except ImportError:
    pass  # J2534 support not available

