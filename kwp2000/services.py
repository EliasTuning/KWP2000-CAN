"""Service definitions for KWP2000."""

from typing import Optional
from dataclasses import dataclass
from kwp2000.request import Request
from kwp2000.response import Response
from kwp2000.constants import (
    SERVICE_START_COMMUNICATION,
    SERVICE_STOP_COMMUNICATION,
    SERVICE_ACCESS_TIMING_PARAMETER,
    SERVICE_SEND_DATA,
    SERVICE_START_DIAGNOSTIC_SESSION,
    SERVICE_ROUTINE_CONTROL,
    SERVICE_ECU_RESET,
    SERVICE_READ_DATA_BY_LOCAL_IDENTIFIER,
    SERVICE_READ_MEMORY_BY_ADDRESS,
)


class ServiceBase:
    """Base class for services."""
    
    @classmethod
    def make_request(cls, *args, **kwargs) -> Request:
        """Create a request for this service."""
        raise NotImplementedError
    
    @classmethod
    def interpret_response(cls, response: Response):
        """Interpret a response for this service."""
        raise NotImplementedError


class RoutineControl(ServiceBase):
    """RoutineControl service (0x31)."""
    
    SERVICE_ID = SERVICE_ROUTINE_CONTROL
    
    class ControlType:
        """Control type constants."""
        startRoutine = 1
        stopRoutine = 2
        requestRoutineResults = 3
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        control_type_echo: int
        routine_id_echo: int
    
    @classmethod
    def make_request(
        cls,
        control_type: int,
        routine_id: int
    ) -> Request:
        """
        Create a RoutineControl request.
        
        Args:
            control_type: Control type (1=start, 2=stop, 3=request results)
            routine_id: Routine ID (2 bytes, big-endian)
            
        Returns:
            Request object
        """
        # Routine ID is 2 bytes, big-endian
        routine_id_high = (routine_id >> 8) & 0xFF
        routine_id_low = routine_id & 0xFF
        
        data = bytes([control_type, routine_id_high, routine_id_low])
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'RoutineControl.ServiceData':
        """
        Interpret a RoutineControl response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 3:
            raise ValueError("Invalid response data length")
        
        control_type_echo = response.data[0]
        routine_id_high = response.data[1]
        routine_id_low = response.data[2]
        routine_id_echo = (routine_id_high << 8) | routine_id_low
        
        return cls.ServiceData(
            control_type_echo=control_type_echo,
            routine_id_echo=routine_id_echo
        )


class ECUReset(ServiceBase):
    """ECUReset service (0x11)."""
    
    SERVICE_ID = SERVICE_ECU_RESET
    
    @classmethod
    def make_request(
        cls,
        reset_type: int
    ) -> Request:
        """
        Create an ECUReset request.
        
        Args:
            reset_type: Reset type
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([reset_type]))
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret an ECUReset response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) > 0:
            result['reset_type_echo'] = response.data[0]
        
        return result


class StartCommunication(ServiceBase):
    """StartCommunication service (0x81)."""
    
    SERVICE_ID = SERVICE_START_COMMUNICATION
    
    @classmethod
    def make_request(
        cls,
        key_bytes: Optional[bytes] = None
    ) -> Request:
        """
        Create a StartCommunication request.
        
        Args:
            key_bytes: Optional key bytes (typically 2 bytes)
            
        Returns:
            Request object
        """
        data = key_bytes if key_bytes else b''
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a StartCommunication response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data (key bytes, etc.)
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) >= 2:
            result['key_byte_1'] = response.data[0]
            result['key_byte_2'] = response.data[1]
        
        return result


class StopCommunication(ServiceBase):
    """StopCommunication service (0x82)."""
    
    SERVICE_ID = SERVICE_STOP_COMMUNICATION
    
    @classmethod
    def make_request(cls) -> Request:
        """
        Create a StopCommunication request.
        
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, b'')
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a StopCommunication response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        return {}


class AccessTimingParameter(ServiceBase):
    """AccessTimingParameter service (0x83)."""
    
    SERVICE_ID = SERVICE_ACCESS_TIMING_PARAMETER
    
    @classmethod
    def make_request(
        cls,
        timing_parameter_id: int,
        timing_values: Optional[bytes] = None
    ) -> Request:
        """
        Create an AccessTimingParameter request.
        
        Args:
            timing_parameter_id: Timing parameter ID (0=read limits, 3=set parameters)
            timing_values: Optional timing values to set
            
        Returns:
            Request object
        """
        data = bytes([timing_parameter_id])
        if timing_values:
            data += timing_values
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret an AccessTimingParameter response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) > 0:
            result['timing_parameter_id_echo'] = response.data[0]
            if len(response.data) > 1:
                result['timing_values'] = response.data[1:]
        
        return result


class SendData(ServiceBase):
    """SendData service (0x84)."""
    
    SERVICE_ID = SERVICE_SEND_DATA
    
    @classmethod
    def make_request(
        cls,
        data: bytes
    ) -> Request:
        """
        Create a SendData request.
        
        Args:
            data: Data bytes to send
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a SendData response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) > 0:
            result['data'] = response.data
        
        return result


class StartDiagnosticSession(ServiceBase):
    """StartDiagnosticSession service (0x10)."""
    
    SERVICE_ID = SERVICE_START_DIAGNOSTIC_SESSION
    
    @classmethod
    def make_request(
        cls,
        session_type: int
    ) -> Request:
        """
        Create a StartDiagnosticSession request.
        
        Args:
            session_type: Session type (e.g., 0x89 for extended diagnostic session)
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([session_type]))
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a StartDiagnosticSession response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data containing:
                - session_type_echo: Echo of the requested session type
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) > 0:
            result['session_type_echo'] = response.data[0]
        
        return result


class ReadDataByLocalIdentifier(ServiceBase):
    """ReadDataByLocalIdentifier service (0x21)."""
    
    SERVICE_ID = SERVICE_READ_DATA_BY_LOCAL_IDENTIFIER
    
    @classmethod
    def make_request(
        cls,
        local_identifier: int
    ) -> Request:
        """
        Create a ReadDataByLocalIdentifier request.
        
        Args:
            local_identifier: Local identifier (1 byte)
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([local_identifier]))
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a ReadDataByLocalIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data containing:
                - local_identifier_echo: Echo of the requested local identifier
                - data: The data bytes read
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) > 0:
            result['local_identifier_echo'] = response.data[0]
            if len(response.data) > 1:
                result['data'] = response.data[1:]
            else:
                result['data'] = b''
        
        return result


class ReadMemoryByAddress(ServiceBase):
    """ReadMemoryByAddress service (0x23)."""
    
    SERVICE_ID = SERVICE_READ_MEMORY_BY_ADDRESS
    
    class TransmissionMode:
        """Transmission mode constants."""
        single = 0x01
        slow = 0x02
        medium = 0x03
        fast = 0x04
        stop = 0x05
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        record_values: bytes
        memory_address_echo: int
    
    @classmethod
    def make_request(
        cls,
        memory_address: int,
        memory_size: int,
        transmission_mode: Optional[int] = None,
        maximum_number_of_responses_to_send: Optional[int] = None
    ) -> Request:
        """
        Create a ReadMemoryByAddress request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Number of bytes to read (1 byte)
            transmission_mode: Optional transmission mode (0x01=single, 0x02=slow, 0x03=medium, 0x04=fast, 0x05=stop)
            maximum_number_of_responses_to_send: Optional maximum number of responses (only if transmission_mode is provided)
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        # Build request data
        data = bytes([
            memory_address_high,
            memory_address_middle,
            memory_address_low,
            memory_size & 0xFF
        ])
        
        # Add optional transmission mode
        if transmission_mode is not None:
            data += bytes([transmission_mode])
            # Add optional maximum number of responses to send
            if maximum_number_of_responses_to_send is not None:
                data += bytes([maximum_number_of_responses_to_send])
        
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadMemoryByAddress.ServiceData':
        """
        Interpret a ReadMemoryByAddress response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data containing:
                - record_values: The memory data read (bytes)
                - memory_address_echo: Echo of the requested memory address (24-bit)
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        # Response format:
        # Bytes 0..n-4: recordValues
        # Bytes n-3..n-1: memoryAddress echo (High, Middle, Low)
        if len(response.data) < 3:
            raise ValueError("Invalid response data length: must be at least 3 bytes")
        
        # Extract memory address echo (last 3 bytes)
        memory_address_high = response.data[-3]
        memory_address_middle = response.data[-2]
        memory_address_low = response.data[-1]
        memory_address_echo = (memory_address_high << 16) | (memory_address_middle << 8) | memory_address_low
        
        # Extract record values (all bytes except last 3)
        record_values = response.data[:-3]
        
        return cls.ServiceData(
            record_values=record_values,
            memory_address_echo=memory_address_echo
        )


class ReadMemoryByAddress2(ServiceBase):
    """ReadMemoryByAddress2 service (0x23) - variant with memory type."""
    
    SERVICE_ID = SERVICE_READ_MEMORY_BY_ADDRESS
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        record_values: bytes
    
    @classmethod
    def make_request(
        cls,
        memory_address: int,
        memory_type: int,
        memory_size: int
    ) -> Request:
        """
        Create a ReadMemoryByAddress2 request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_type: Memory type (1 byte)
            memory_size: Number of bytes to read (1 byte)
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        # Build request data
        data = bytes([
            memory_address_high,
            memory_address_middle,
            memory_address_low,
            memory_type & 0xFF,
            memory_size & 0xFF
        ])
        
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadMemoryByAddress2.ServiceData':
        """
        Interpret a ReadMemoryByAddress2 response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data containing:
                - record_values: The memory data read (bytes)
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        # Response format:
        # Bytes 0..n-1: recordValues (no address echo)
        record_values = response.data
        
        return cls.ServiceData(
            record_values=record_values
        )

