"""
DCAN CAN connection adapter for KWP2000-CAN.

This module provides a CAN connection adapter that wraps the DCAN CanAdapter
to implement the CanConnection interface for use with KWP2000 protocols.
"""

from .can_adapter import CanAdapter, CanAdapterError, CanAdapterTimeout, CanAdapterChecksumError
from .can_connection import DCanCanConnection

__all__ = [
    'CanAdapter',
    'CanAdapterError',
    'CanAdapterTimeout',
    'CanAdapterChecksumError',
    'DCanCanConnection',
]

