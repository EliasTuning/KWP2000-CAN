"""
KWP2000-STAR Python Library

A Python library for KWP2000-STAR communication protocol.
"""

from .transport import KWP2000StarTransportCAN
from .constants import START_BYTE, TARGET_ADDR, SRC_ADDR

# Optional imports from serial module (may fail if pyserial not installed)
try:
    from kwp2000_can.protocols.serial.kwp2000_star_serial.frames import build_frame, parse_frame, calculate_checksum
    _HAS_SERIAL_FRAMES = True
except ImportError:
    _HAS_SERIAL_FRAMES = False
    build_frame = None
    parse_frame = None
    calculate_checksum = None

__version__ = "0.1.0"

__all__ = [
    'KWP2000StarTransportCAN',
    'START_BYTE',
    'TARGET_ADDR',
    'SRC_ADDR',
]

# Add frame functions to __all__ only if available
if _HAS_SERIAL_FRAMES:
    __all__.extend(['build_frame', 'parse_frame', 'calculate_checksum'])
