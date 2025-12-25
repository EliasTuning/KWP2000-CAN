"""
TP20 (VW Transport Protocol 2.0) Python Library

A Python library for TP20 transport protocol over CAN bus.
Sends and receives byte data directly over CAN using TP20 protocol.
"""

from kwp2000_can.interface.base_can_connection import CanConnection, MockCanConnection
from .transport import TP20Transport
from .exceptions import (
    TP20Exception,
    TP20TimeoutException,
    TP20ChannelException,
    TP20InvalidFrameException,
    TP20NegativeResponseException,
    TP20DisconnectedException,
)
from .timing import TimingParameter, TimingUnits

__version__ = "0.1.0"

__all__ = [
    'TP20Transport',
    'CanConnection',
    'MockCanConnection',
    'TimingParameter',
    'TimingUnits',
    'TP20Exception',
    'TP20TimeoutException',
    'TP20ChannelException',
    'TP20InvalidFrameException',
    'TP20NegativeResponseException',
    'TP20DisconnectedException',
]

