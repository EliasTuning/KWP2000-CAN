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
    SERVICE_TESTER_PRESENT,
    SERVICE_READ_DATA_BY_LOCAL_IDENTIFIER,
    SERVICE_READ_MEMORY_BY_ADDRESS,
    DIAGNOSTIC_MODE_OBD2,
    DIAGNOSTIC_MODE_ECU_PROGRAMMING,
    DIAGNOSTIC_MODE_ECU_DEVELOPMENT,
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


class TesterPresent(ServiceBase):
    """TesterPresent service (0x3E)."""
    
    SERVICE_ID = SERVICE_TESTER_PRESENT
    POSITIVE_RESPONSE_SERVICE_ID = 0x7E  # TPPR (TesterPresent Positive Response)
    
    class ResponseRequired:
        """Response required constants."""
        YES = 0x01  # Server shall send a response
        NO = 0x02   # Server shall not send a response
    
    @classmethod
    def make_request(
        cls,
        response_required: int = ResponseRequired.YES
    ) -> Request:
        """
        Create a TesterPresent request.
        
        According to KWP2000 specification:
        - Byte #1: Service ID = 0x3E (TP)
        - Byte #2: responseRequired (0x01 = yes, 0x02 = no)
        
        Args:
            response_required: Response required flag (0x01 = yes, 0x02 = no, default: 0x01)
            
        Returns:
            Request object
        """
        if response_required not in (cls.ResponseRequired.YES, cls.ResponseRequired.NO):
            raise ValueError(
                f"Invalid response_required value: 0x{response_required:02X}. "
                f"Must be 0x01 (yes) or 0x02 (no)"
            )
        
        data = bytes([response_required])
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a TesterPresent response.
        
        Positive Response format:
        - Byte #1: Service ID = 0x7E (TPPR)
        - No data bytes
        
        Negative Response format:
        - Byte #1: 0x7F (NR)
        - Byte #2: 0x3E (TesterPresent service ID)
        - Byte #3: Response code
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data (empty for positive response)
            
        Raises:
            ValueError: If response is not positive
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        # Positive response has no data bytes
        return {}


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
    POSITIVE_RESPONSE_SERVICE_ID = 0xC3  # ATPPR (AccessTimingParameter Positive Response)
    
    # Timing Parameter Identifier constants
    TPI_SP = 0x03  # Set Parameters
    
    @dataclass
    class TimingParameters:
        """Timing parameters structure.
        
        According to KWP2000 ISO 14230-3:
        - P1 = Bytezwischenzeit des Antworttelegramms (0-20ms)
        - P2 = Zeit zwischen Request und Antworttelegramm bzw. Zeit zwischen 2 Antworttelegrammen (25-50ms)
        - P3 = Zeit zwischen Antworttelegrammende und neuem Request (55-µms)
        - P4 = Bytezwischenzeit des Requesttelegramms (0-20ms)
        """
        p2min: int  # P2min: Minimum Zeit zwischen Request und Antworttelegramm bzw. Zeit zwischen 2 Antworttelegrammen (0.5 ms units, e.g., 0x32 = 25 ms)
        p2max: int  # P2max: Maximum Zeit zwischen Request und Antworttelegramm bzw. Zeit zwischen 2 Antworttelegrammen (25 ms units, e.g., 0x02 = 50 ms)
        p3min: int  # P3min: Minimum Zeit zwischen Antworttelegrammende und neuem Request (0.5 ms units, e.g., 0x6E = 55 ms)
        p3max: int  # P3max: Maximum Zeit zwischen Antworttelegrammende und neuem Request (250 ms units, e.g., 0x14 = 5000 ms)
        p4min: int  # P4min: Bytezwischenzeit des Requesttelegramms (0.5 ms units, e.g., 0x0A = 5 ms)
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        timing_parameter_id: int
        timing_parameters: Optional['AccessTimingParameter.TimingParameters'] = None
    
    @classmethod
    def make_request(
        cls,
        timing_parameter_id: int = TPI_SP,
        p2min: int = 0x32,
        p2max: int = 0x02,
        p3min: int = 0x6E,
        p3max: int = 0x14,
        p4min: int = 0x0A
    ) -> Request:
        """
        Create an AccessTimingParameter request.
        
        According to KWP2000 ISO 14230-3 specification:
        - Byte #1: Service ID = 0x83 (ATP)
        - Byte #2: TimingParameterIdentifier = 0x03 (TPI_SP)
        - Byte #3: P2min = 0x32 (25 ms with 0.5 ms resolution)
          P2 = Zeit zwischen Request und Antworttelegramm bzw. Zeit zwischen 2 Antworttelegrammen (25-50ms)
        - Byte #4: P2max = 0x02 (50 ms with 25 ms resolution)
        - Byte #5: P3min = 0x6E (55 ms with 0.5 ms resolution)
          P3 = Zeit zwischen Antworttelegrammende und neuem Request (55-µms)
        - Byte #6: P3max = 0x14 (5000 ms with 250 ms resolution)
        - Byte #7: P4min = 0x0A (5 ms with 0.5 ms resolution)
          P4 = Bytezwischenzeit des Requesttelegramms (0-20ms)
        
        Note: P1 = Bytezwischenzeit des Antworttelegramms (0-20ms) is not part of this service.
        
        Args:
            timing_parameter_id: Timing parameter identifier (default: 0x03 = TPI_SP)
            p2min: P2min value - Minimum Zeit zwischen Request und Antworttelegramm (default: 0x32 = 25 ms)
            p2max: P2max value - Maximum Zeit zwischen Request und Antworttelegramm (default: 0x02 = 50 ms)
            p3min: P3min value - Minimum Zeit zwischen Antworttelegrammende und neuem Request (default: 0x6E = 55 ms)
            p3max: P3max value - Maximum Zeit zwischen Antworttelegrammende und neuem Request (default: 0x14 = 5000 ms)
            p4min: P4min value - Bytezwischenzeit des Requesttelegramms (default: 0x0A = 5 ms)
            
        Returns:
            Request object
        """
        data = bytes([
            timing_parameter_id,
            p2min,
            p2max,
            p3min,
            p3max,
            p4min
        ])
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def make_request_with_timing_parameters(
        cls,
        timing_parameter_id: int = TPI_SP,
        timing_parameters: Optional['AccessTimingParameter.TimingParameters'] = None
    ) -> Request:
        """
        Create an AccessTimingParameter request with TimingParameters object.
        
        Args:
            timing_parameter_id: Timing parameter identifier (default: 0x03 = TPI_SP)
            timing_parameters: TimingParameters object (default: uses standard values)
            
        Returns:
            Request object
        """
        if timing_parameters is None:
            timing_parameters = cls.TimingParameters(
                p2min=0x32,
                p2max=0x02,
                p3min=0x6E,
                p3max=0x14,
                p4min=0x0A
            )
        
        return cls.make_request(
            timing_parameter_id=timing_parameter_id,
            p2min=timing_parameters.p2min,
            p2max=timing_parameters.p2max,
            p3min=timing_parameters.p3min,
            p3max=timing_parameters.p3max,
            p4min=timing_parameters.p4min
        )
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'AccessTimingParameter.ServiceData':
        """
        Interpret an AccessTimingParameter response.
        
        Positive Response format:
        - Byte #1: Service ID = 0xC3 (ATPPR)
        - Byte #2: TimingParameterIdentifier = 0x03 (TPI_SP)
        - Byte #3: P2min = 0x32 (25 ms with 0.5 ms resolution)
          P2 = Zeit zwischen Request und Antworttelegramm bzw. Zeit zwischen 2 Antworttelegrammen (25-50ms)
        - Byte #4: P2max = 0x02 (50 ms with 25 ms resolution)
        - Byte #5: P3min = 0x6E (55 ms with 0.5 ms resolution)
          P3 = Zeit zwischen Antworttelegrammende und neuem Request (55-µms)
        - Byte #6: P3max = 0x14 (5000 ms with 250 ms resolution)
        - Byte #7: P4min = 0x0A (5 ms with 0.5 ms resolution)
          P4 = Bytezwischenzeit des Requesttelegramms (0-20ms)
        
        Negative Response format:
        - Byte #1: 0x7F (NR)
        - Byte #2: 0x03 (TPI_SP)
        - Byte #3: Response code (0x10 = generalReject, 0x12 = subFunctionNotSupported)
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        # Positive response should have at least 6 bytes:
        # timing_parameter_id (1 byte) + 5 timing parameter bytes
        if len(response.data) < 6:
            raise ValueError(f"Invalid response data length: expected at least 6 bytes, got {len(response.data)}")
        
        timing_parameter_id = response.data[0]
        
        # Parse timing parameters
        timing_parameters = cls.TimingParameters(
            p2min=response.data[1],
            p2max=response.data[2],
            p3min=response.data[3],
            p3max=response.data[4],
            p4min=response.data[5]
        )
        
        return cls.ServiceData(
            timing_parameter_id=timing_parameter_id,
            timing_parameters=timing_parameters
        )


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
    
    class DiagnosticMode:
        """Diagnostic mode constants."""
        OBD2 = DIAGNOSTIC_MODE_OBD2  # Standardmodus OBD2-Modus (DT-SD-OBDIIMD)
        ECU_PROGRAMMING = DIAGNOSTIC_MODE_ECU_PROGRAMMING  # Steuergeräte Programmiermodus (ECUPM)
        ECU_DEVELOPMENT = DIAGNOSTIC_MODE_ECU_DEVELOPMENT  # SG-Entwicklungs Modus (ECUDM)
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        diagnostic_mode: int
        baudrate_identifier: Optional[int] = None
    
    @classmethod
    def make_request(
        cls,
        diagnostic_mode: Optional[int] = None,
        baudrate_identifier: Optional[int] = None,
        session_type: Optional[int] = None  # Backward compatibility alias
    ) -> Request:
        """
        Create a StartDiagnosticSession request.
        
        Args:
            diagnostic_mode: Diagnostic mode (0x81=OBD2, 0x85=ECU Programming, 0x86=ECU Development)
            baudrate_identifier: Optional baudrate identifier (0x01=9600, 0x02=19200, etc.)
            session_type: Backward compatibility alias for diagnostic_mode
            
        Returns:
            Request object
            
        Raises:
            ValueError: If neither diagnostic_mode nor session_type is provided
        """
        # Support backward compatibility: if session_type is provided, use it as diagnostic_mode
        if session_type is not None:
            diagnostic_mode = session_type
        
        if diagnostic_mode is None:
            raise ValueError("diagnostic_mode or session_type must be provided")
        
        # Build request data: diagnosticMode (mandatory) + baudrateIdentifier (optional)
        data = bytes([diagnostic_mode])
        if baudrate_identifier is not None:
            data += bytes([baudrate_identifier])
        
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a StartDiagnosticSession response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data containing:
                - diagnostic_mode: Echo of the requested diagnostic mode
                - baudrate_identifier: Echo of the requested baudrate identifier (if present)
                - session_type_echo: Backward compatibility alias for diagnostic_mode
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        diagnostic_mode = response.data[0]
        baudrate_identifier = None
        
        if len(response.data) >= 2:
            baudrate_identifier = response.data[1]
        
        result = {
            'diagnostic_mode': diagnostic_mode,
            'session_type_echo': diagnostic_mode  # Backward compatibility
        }
        
        if baudrate_identifier is not None:
            result['baudrate_identifier'] = baudrate_identifier
        
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

