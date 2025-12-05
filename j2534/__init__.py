"""
J2534 Python Library

A Python library for J2534 Pass-Thru interface communication,
providing CAN bus access for automotive diagnostics.
"""

from j2534.j2534 import (
    J2534,
    Error_ID,
    Protocol_ID,
    Filter,
    TxStatusFlag,
    Ioctl_ID,
    Ioctl_Parameters,
    Ioctl_Flags,
    SCONFIG,
    PASSTHRU_MSG,
)
from j2534.j2534_connection import J2534Connection
from j2534.can_connection import J2534CanConnection
from j2534.j2534_detect import J2534RegistryDetector, PassThruDeviceInfo

__version__ = "0.1.0"

__all__ = [
    'J2534',
    'J2534Connection',
    'J2534CanConnection',
    'J2534RegistryDetector',
    'PassThruDeviceInfo',
    'Error_ID',
    'Protocol_ID',
    'Filter',
    'TxStatusFlag',
    'Ioctl_ID',
    'Ioctl_Parameters',
    'Ioctl_Flags',
    'SCONFIG',
    'PASSTHRU_MSG',
]

