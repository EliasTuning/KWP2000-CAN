"""
KWP2000-STAR Python Library

A Python library for KWP2000-STAR communication protocol.
"""

from .frames import build_frame, parse_frame, calculate_checksum
from .constants import (
    START_BYTE,
    TARGET_ADDR,
    SRC_ADDR,
)
from . import exceptions
from .transport import KWP2000StarTransport

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
