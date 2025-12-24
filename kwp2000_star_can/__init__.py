"""
KWP2000-STAR Python Library

A Python library for KWP2000-STAR communication protocol.
"""

from kwp2000_star_serial.frames import build_frame, parse_frame, calculate_checksum
from kwp2000_star_serial.constants import (
    START_BYTE,
    TARGET_ADDR,
    SRC_ADDR,
)
from kwp2000_star_serial import exceptions
from kwp2000_star_serial.transport import KWP2000StarTransport

__version__ = "0.1.0"

__all__ = [
    'build_frame',
    'parse_frame',
    'calculate_checksum',
    'START_BYTE',
    'TARGET_ADDR',
    'SRC_ADDR',
    'exceptions',
    'KWP2000StarTransport',
]
