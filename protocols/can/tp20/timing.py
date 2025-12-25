"""Timing parameter helper functions for TP20 T1 and T3 parameters."""

from enum import IntEnum
from typing import Tuple


class TimingUnits(IntEnum):
    """Timing units for T1 and T3 parameters (bits 7-6)."""
    MS_0_1 = 0x0  # 0.1ms
    MS_1 = 0x1    # 1ms
    MS_10 = 0x2   # 10ms
    MS_100 = 0x3  # 100ms


class TimingParameter:
    """
    Helper class for encoding and decoding TP20 timing parameters (T1 and T3).
    
    Format:
        Bits 7-6: Units (0x0=0.1ms, 0x1=1ms, 0x2=10ms, 0x3=100ms)
        Bits 5-0: Scale (0-63, number to multiply units by)
    
    Usage:
        # Decode a byte value to milliseconds
        time_ms = TimingParameter.decode(0x8A)
        
        # Encode milliseconds to a byte value
        byte_value = TimingParameter.encode(10.0)
        
        # Extract units and scale
        units, scale = TimingParameter.parse(0x8A)
    """
    
    # Unit values in milliseconds
    UNIT_VALUES = {
        TimingUnits.MS_0_1: 0.1,
        TimingUnits.MS_1: 1.0,
        TimingUnits.MS_10: 10.0,
        TimingUnits.MS_100: 100.0,
    }
    
    # Masks for extracting bits
    UNITS_MASK = 0xC0  # Bits 7-6
    SCALE_MASK = 0x3F  # Bits 5-0
    
    @staticmethod
    def decode(byte_value: int) -> float:
        """
        Decode a timing parameter byte value to milliseconds.
        
        Args:
            byte_value: Single byte timing parameter (0x00-0xFF)
            
        Returns:
            Time in milliseconds
            
        Example:
            >>> TimingParameter.decode(0x8A)
            10.0
        """
        if not 0 <= byte_value <= 0xFF:
            raise ValueError(f"Byte value must be between 0x00 and 0xFF, got 0x{byte_value:02X}")
        
        units_code = (byte_value & TimingParameter.UNITS_MASK) >> 6
        scale = byte_value & TimingParameter.SCALE_MASK
        
        try:
            units = TimingUnits(units_code)
        except ValueError:
            raise ValueError(f"Invalid units code: 0x{units_code:X}")
        
        unit_value = TimingParameter.UNIT_VALUES[units]
        return unit_value * scale
    
    @staticmethod
    def encode(time_ms: float) -> int:
        """
        Encode milliseconds to a timing parameter byte value.
        
        Args:
            time_ms: Time in milliseconds (must be >= 0)
            
        Returns:
            Single byte timing parameter value
            
        Example:
            >>> TimingParameter.encode(10.0)
            138  # 0x8A
        """
        if time_ms < 0:
            raise ValueError(f"Time must be >= 0, got {time_ms}")
        
        if time_ms == 0:
            return 0x00
        
        # Try each unit size and find the best fit
        best_byte = None
        best_error = float('inf')
        
        for units in TimingUnits:
            unit_value = TimingParameter.UNIT_VALUES[units]
            scale = round(time_ms / unit_value)
            
            # Scale must fit in 6 bits (0-63)
            if scale > 63:
                continue
            
            encoded_time = unit_value * scale
            error = abs(time_ms - encoded_time)
            
            if error < best_error:
                best_error = error
                units_code = units.value << 6
                best_byte = units_code | scale
        
        if best_byte is None:
            # Use maximum value (100ms * 63 = 6300ms)
            return 0xFF
        
        return best_byte
    
    @staticmethod
    def parse(byte_value: int) -> Tuple[TimingUnits, int]:
        """
        Parse a timing parameter byte value into units and scale.
        
        Args:
            byte_value: Single byte timing parameter (0x00-0xFF)
            
        Returns:
            Tuple of (TimingUnits, scale)
            
        Example:
            >>> TimingParameter.parse(0x8A)
            (<TimingUnits.MS_1: 1>, 10)
        """
        if not 0 <= byte_value <= 0xFF:
            raise ValueError(f"Byte value must be between 0x00 and 0xFF, got 0x{byte_value:02X}")
        
        units_code = (byte_value & TimingParameter.UNITS_MASK) >> 6
        scale = byte_value & TimingParameter.SCALE_MASK
        
        try:
            units = TimingUnits(units_code)
        except ValueError:
            raise ValueError(f"Invalid units code: 0x{units_code:X}")
        
        return units, scale
    
    @staticmethod
    def get_units_name(byte_value: int) -> str:
        """
        Get a human-readable name for the units in a timing parameter.
        
        Args:
            byte_value: Single byte timing parameter (0x00-0xFF)
            
        Returns:
            String description of the units
            
        Example:
            >>> TimingParameter.get_units_name(0x8A)
            '1ms'
        """
        units, _ = TimingParameter.parse(byte_value)
        return TimingParameter.UNIT_VALUES[units].__str__().replace('.0', '') + 'ms'

