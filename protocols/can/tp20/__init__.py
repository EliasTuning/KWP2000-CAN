"""
TP20 (VW Transport Protocol 2.0) Python Library

A Python library for TP20 transport protocol over CAN bus.
Sends and receives byte data directly over CAN using TP20 protocol.
"""

from protocols.can.tp20.can_connection import CanConnection, MockCanConnection

__version__ = "0.1.0"

__all__ = [
    'TP20Transport',
    'CanConnection',
    'MockCanConnection',
    'TimingParameter',
    'TimingUnits',
]

