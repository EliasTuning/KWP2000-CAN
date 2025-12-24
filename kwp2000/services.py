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
    SERVICE_STOP_DIAGNOSTIC_SESSION,
    SERVICE_ROUTINE_CONTROL,
    SERVICE_STOP_ROUTINE_BY_LOCAL_IDENTIFIER,
    SERVICE_REQUEST_ROUTINE_RESULTS_BY_LOCAL_IDENTIFIER,
    SERVICE_START_ROUTINE_BY_ADDRESS,
    SERVICE_STOP_ROUTINE_BY_ADDRESS,
    SERVICE_REQUEST_ROUTINE_RESULTS_BY_ADDRESS,
    SERVICE_ECU_RESET,
    SERVICE_TESTER_PRESENT,
    SERVICE_READ_DATA_BY_LOCAL_IDENTIFIER,
    SERVICE_READ_DATA_BY_COMMON_IDENTIFIER,
    SERVICE_READ_MEMORY_BY_ADDRESS,
    SERVICE_SET_DATA_RATES,
    SERVICE_WRITE_DATA_BY_COMMON_IDENTIFIER,
    SERVICE_WRITE_DATA_BY_LOCAL_IDENTIFIER,
    SERVICE_WRITE_MEMORY_BY_ADDRESS,
    SERVICE_READ_FREEZE_FRAME_DATA,
    SERVICE_READ_DIAGNOSTIC_TROUBLE_CODES,
    SERVICE_CLEAR_DIAGNOSTIC_INFORMATION,
    SERVICE_READ_STATUS_OF_DIAGNOSTIC_TROUBLE_CODES,
    SERVICE_READ_DIAGNOSTIC_TROUBLE_CODES_BY_STATUS,
    SERVICE_INPUT_OUTPUT_CONTROL_BY_COMMON_IDENTIFIER,
    SERVICE_INPUT_OUTPUT_CONTROL_BY_LOCAL_IDENTIFIER,
    SERVICE_REQUEST_DOWNLOAD,
    SERVICE_REQUEST_UPLOAD,
    SERVICE_TRANSFER_DATA,
    SERVICE_REQUEST_TRANSFER_EXIT,
    SERVICE_SECURITY_ACCESS,
    SERVICE_READ_ECU_IDENTIFICATION,
    SERVICE_DYNAMICALLY_DEFINE_LOCAL_IDENTIFIER,
    SERVICE_ESC_CODE,
    DIAGNOSTIC_MODE_OBD2,
    DIAGNOSTIC_MODE_ECU_PROGRAMMING,
    DIAGNOSTIC_MODE_ECU_DEVELOPMENT,
    TimingParameters,
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
    class ServiceData:
        """Parsed service data from response."""
        timing_parameter_id: int
        timing_parameters: Optional[TimingParameters] = None
    
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
        timing_parameters: Optional[TimingParameters] = None
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
            from kwp2000.constants import TIMING_PARAMETER_STANDARD
            timing_parameters = TIMING_PARAMETER_STANDARD
        
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
        timing_parameters = TimingParameters(
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


# ============================================================================
# Session Control Services
# ============================================================================

class StopDiagnosticSession(ServiceBase):
    """StopDiagnosticSession service (0x20)."""
    
    SERVICE_ID = SERVICE_STOP_DIAGNOSTIC_SESSION
    
    @classmethod
    def make_request(cls) -> Request:
        """
        Create a StopDiagnosticSession request.
        
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, b'')
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a StopDiagnosticSession response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data (empty for positive response)
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        return {}


# ============================================================================
# Diagnostic Trouble Code Services
# ============================================================================

class ReadFreezeFrameData(ServiceBase):
    """ReadFreezeFrameData service (0x12)."""
    
    SERVICE_ID = SERVICE_READ_FREEZE_FRAME_DATA
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        freeze_frame_number: int
        data: bytes
    
    @classmethod
    def make_request(cls, freeze_frame_number: int) -> Request:
        """
        Create a ReadFreezeFrameData request.
        
        Args:
            freeze_frame_number: Freeze frame number (1 byte)
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([freeze_frame_number]))
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadFreezeFrameData.ServiceData':
        """
        Interpret a ReadFreezeFrameData response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        freeze_frame_number = response.data[0]
        data = response.data[1:] if len(response.data) > 1 else b''
        
        return cls.ServiceData(
            freeze_frame_number=freeze_frame_number,
            data=data
        )


class ReadDiagnosticTroubleCodes(ServiceBase):
    """ReadDiagnosticTroubleCodes service (0x13)."""
    
    SERVICE_ID = SERVICE_READ_DIAGNOSTIC_TROUBLE_CODES
    
    @dataclass
    class DTC:
        """Diagnostic Trouble Code."""
        code: int  # 2-byte DTC code
        status: Optional[int] = None  # Status byte if available
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        dtcs: list  # List of DTC objects
    
    @classmethod
    def make_request(cls) -> Request:
        """
        Create a ReadDiagnosticTroubleCodes request.
        
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, b'')
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadDiagnosticTroubleCodes.ServiceData':
        """
        Interpret a ReadDiagnosticTroubleCodes response.
        
        Response format: DTC count (1 byte) + DTCs (2 bytes each)
        or: DTCs (2 bytes each) without count
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed DTCs
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) == 0:
            return cls.ServiceData(dtcs=[])
        
        dtcs = []
        data = response.data
        
        # Check if first byte is DTC count
        # If data length is odd, first byte is likely DTC count
        # If data length is even, all bytes are DTC pairs
        if len(data) % 2 == 1:
            # First byte is DTC count, rest are DTC pairs
            dtc_count = data[0]
            dtc_data = data[1:]
        else:
            # All bytes are DTC pairs
            dtc_count = None
            dtc_data = data
        
        # Parse DTC pairs (2 bytes each)
        for i in range(0, len(dtc_data), 2):
            if i + 1 < len(dtc_data):
                dtc_high = dtc_data[i]
                dtc_low = dtc_data[i + 1]
                dtc_code = (dtc_high << 8) | dtc_low
                dtcs.append(cls.DTC(code=dtc_code))
        
        return cls.ServiceData(dtcs=dtcs)


class ClearDiagnosticInformation(ServiceBase):
    """ClearDiagnosticInformation service (0x14)."""
    
    SERVICE_ID = SERVICE_CLEAR_DIAGNOSTIC_INFORMATION
    
    @classmethod
    def make_request(cls, group_of_dtc: int) -> Request:
        """
        Create a ClearDiagnosticInformation request.
        
        Args:
            group_of_dtc: Group of DTC to clear (1 byte)
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([group_of_dtc]))
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret a ClearDiagnosticInformation response.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary with parsed response data
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        result = {}
        if len(response.data) > 0:
            result['group_of_dtc_echo'] = response.data[0]
        
        return result


class ReadStatusOfDiagnosticTroubleCodes(ServiceBase):
    """ReadStatusOfDiagnosticTroubleCodes service (0x17)."""
    
    SERVICE_ID = SERVICE_READ_STATUS_OF_DIAGNOSTIC_TROUBLE_CODES
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        status: int  # Status byte
        
    @classmethod
    def make_request(cls) -> Request:
        """
        Create a ReadStatusOfDiagnosticTroubleCodes request.
        
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, b'')
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadStatusOfDiagnosticTroubleCodes.ServiceData':
        """
        Interpret a ReadStatusOfDiagnosticTroubleCodes response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with status byte
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        return cls.ServiceData(status=response.data[0])


class ReadDiagnosticTroubleCodesByStatus(ServiceBase):
    """ReadDiagnosticTroubleCodesByStatus service (0x18)."""
    
    SERVICE_ID = SERVICE_READ_DIAGNOSTIC_TROUBLE_CODES_BY_STATUS
    
    @dataclass
    class DTC:
        """Diagnostic Trouble Code with status."""
        code: int  # 2-byte DTC code
        status: int  # Status byte
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        dtcs: list  # List of DTC objects
    
    @classmethod
    def make_request(cls, status_mask: int) -> Request:
        """
        Create a ReadDiagnosticTroubleCodesByStatus request.
        
        Args:
            status_mask: Status mask byte
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([status_mask]))
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadDiagnosticTroubleCodesByStatus.ServiceData':
        """
        Interpret a ReadDiagnosticTroubleCodesByStatus response.
        
        Response format: DTC count (1 byte) + DTCs (3 bytes each: 2 bytes code + 1 byte status)
        or: DTCs (3 bytes each) without count
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed DTCs
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) == 0:
            return cls.ServiceData(dtcs=[])
        
        dtcs = []
        data = response.data
        
        # Check if first byte is DTC count
        # If data length % 3 == 1, first byte is likely DTC count
        # If data length % 3 == 0, all bytes are DTC triplets
        if len(data) % 3 == 1:
            # First byte is DTC count, rest are DTC triplets
            dtc_count = data[0]
            dtc_data = data[1:]
        else:
            # All bytes are DTC triplets
            dtc_count = None
            dtc_data = data
        
        # Parse DTC triplets (2 bytes code + 1 byte status)
        for i in range(0, len(dtc_data), 3):
            if i + 2 < len(dtc_data):
                dtc_high = dtc_data[i]
                dtc_low = dtc_data[i + 1]
                dtc_code = (dtc_high << 8) | dtc_low
                status = dtc_data[i + 2]
                dtcs.append(cls.DTC(code=dtc_code, status=status))
        
        return cls.ServiceData(dtcs=dtcs)


# ============================================================================
# Data Transmission Services
# ============================================================================

class ReadDataByCommonIdentifier(ServiceBase):
    """ReadDataByCommonIdentifier service (0x22)."""
    
    SERVICE_ID = SERVICE_READ_DATA_BY_COMMON_IDENTIFIER
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        common_identifier_echo: int
        data: bytes
    
    @classmethod
    def make_request(cls, common_identifier: int) -> Request:
        """
        Create a ReadDataByCommonIdentifier request.
        
        Args:
            common_identifier: Common identifier (1 byte)
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, common_identifier.to_bytes(2, byteorder='big'))
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadDataByCommonIdentifier.ServiceData':
        """
        Interpret a ReadDataByCommonIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        common_identifier_echo = response.data[0]
        data = response.data[1:] if len(response.data) > 1 else b''
        
        return cls.ServiceData(
            common_identifier_echo=common_identifier_echo,
            data=data
        )


class SetDataRates(ServiceBase):
    """SetDataRates service (0x26)."""
    
    SERVICE_ID = SERVICE_SET_DATA_RATES
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        data_rate_identifier_echo: int
    
    @classmethod
    def make_request(cls, data_rate_identifier: int) -> Request:
        """
        Create a SetDataRates request.
        
        Args:
            data_rate_identifier: Data rate identifier (1 byte)
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([data_rate_identifier]))
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'SetDataRates.ServiceData':
        """
        Interpret a SetDataRates response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        return cls.ServiceData(data_rate_identifier_echo=response.data[0])


class WriteDataByCommonIdentifier(ServiceBase):
    """WriteDataByCommonIdentifier service (0x2E)."""
    
    SERVICE_ID = SERVICE_WRITE_DATA_BY_COMMON_IDENTIFIER
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        common_identifier_echo: int
    
    @classmethod
    def make_request(cls, common_identifier: int, data: bytes) -> Request:
        """
        Create a WriteDataByCommonIdentifier request.
        
        Args:
            common_identifier: Common identifier (1 byte)
            data: Data bytes to write
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([common_identifier]) + data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'WriteDataByCommonIdentifier.ServiceData':
        """
        Interpret a WriteDataByCommonIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        return cls.ServiceData(common_identifier_echo=response.data[0])


class WriteDataByLocalIdentifier(ServiceBase):
    """WriteDataByLocalIdentifier service (0x3B)."""
    
    SERVICE_ID = SERVICE_WRITE_DATA_BY_LOCAL_IDENTIFIER
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        local_identifier_echo: int
    
    @classmethod
    def make_request(cls, local_identifier: int, data: bytes) -> Request:
        """
        Create a WriteDataByLocalIdentifier request.
        
        Args:
            local_identifier: Local identifier (1 byte)
            data: Data bytes to write
            
        Returns:
            Request object
        """
        return Request(cls.SERVICE_ID, bytes([local_identifier]) + data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'WriteDataByLocalIdentifier.ServiceData':
        """
        Interpret a WriteDataByLocalIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        return cls.ServiceData(local_identifier_echo=response.data[0])


class WriteMemoryByAddress(ServiceBase):
    """WriteMemoryByAddress service (0x3D)."""
    
    SERVICE_ID = SERVICE_WRITE_MEMORY_BY_ADDRESS
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_address_echo: int
    
    @classmethod
    def make_request(
        cls,
        memory_address: int,
        memory_size: int,
        data: bytes
    ) -> Request:
        """
        Create a WriteMemoryByAddress request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Number of bytes to write (1 byte)
            data: Data bytes to write
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        # Build request data
        request_data = bytes([
            memory_address_high,
            memory_address_middle,
            memory_address_low,
            memory_size & 0xFF
        ]) + data
        
        return Request(cls.SERVICE_ID, request_data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'WriteMemoryByAddress.ServiceData':
        """
        Interpret a WriteMemoryByAddress response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        # Response format: memoryAddress echo (High, Middle, Low)
        if len(response.data) < 3:
            raise ValueError("Invalid response data length: must be at least 3 bytes")
        
        memory_address_high = response.data[0]
        memory_address_middle = response.data[1]
        memory_address_low = response.data[2]
        memory_address_echo = (memory_address_high << 16) | (memory_address_middle << 8) | memory_address_low
        
        return cls.ServiceData(memory_address_echo=memory_address_echo)


# ============================================================================
# Input/Output Control Services
# ============================================================================

class InputOutputControlByCommonIdentifier(ServiceBase):
    """InputOutputControlByCommonIdentifier service (0x2F)."""
    
    SERVICE_ID = SERVICE_INPUT_OUTPUT_CONTROL_BY_COMMON_IDENTIFIER
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        common_identifier_echo: int
        control_parameter_echo: int
        control_state_echo: Optional[bytes] = None
    
    @classmethod
    def make_request(
        cls,
        common_identifier: int,
        control_parameter: int,
        control_state: Optional[bytes] = None
    ) -> Request:
        """
        Create an InputOutputControlByCommonIdentifier request.
        
        Args:
            common_identifier: Common identifier (1 byte)
            control_parameter: Control parameter (1 byte)
            control_state: Optional control state bytes
            
        Returns:
            Request object
        """
        data = bytes([common_identifier, control_parameter])
        if control_state:
            data += control_state
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'InputOutputControlByCommonIdentifier.ServiceData':
        """
        Interpret an InputOutputControlByCommonIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 2:
            raise ValueError("Invalid response data length: must be at least 2 bytes")
        
        common_identifier_echo = response.data[0]
        control_parameter_echo = response.data[1]
        control_state_echo = response.data[2:] if len(response.data) > 2 else None
        
        return cls.ServiceData(
            common_identifier_echo=common_identifier_echo,
            control_parameter_echo=control_parameter_echo,
            control_state_echo=control_state_echo
        )


class InputOutputControlByLocalIdentifier(ServiceBase):
    """InputOutputControlByLocalIdentifier service (0x30)."""
    
    SERVICE_ID = SERVICE_INPUT_OUTPUT_CONTROL_BY_LOCAL_IDENTIFIER
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        local_identifier_echo: int
        control_parameter_echo: int
        control_state_echo: Optional[bytes] = None
    
    @classmethod
    def make_request(
        cls,
        local_identifier: int,
        control_parameter: int,
        control_state: Optional[bytes] = None
    ) -> Request:
        """
        Create an InputOutputControlByLocalIdentifier request.
        
        Args:
            local_identifier: Local identifier (1 byte)
            control_parameter: Control parameter (1 byte)
            control_state: Optional control state bytes
            
        Returns:
            Request object
        """
        data = bytes([local_identifier, control_parameter])
        if control_state:
            data += control_state
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'InputOutputControlByLocalIdentifier.ServiceData':
        """
        Interpret an InputOutputControlByLocalIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 2:
            raise ValueError("Invalid response data length: must be at least 2 bytes")
        
        local_identifier_echo = response.data[0]
        control_parameter_echo = response.data[1]
        control_state_echo = response.data[2:] if len(response.data) > 2 else None
        
        return cls.ServiceData(
            local_identifier_echo=local_identifier_echo,
            control_parameter_echo=control_parameter_echo,
            control_state_echo=control_state_echo
        )


# ============================================================================
# Routine Control Services (Extended)
# ============================================================================

class StopRoutineByLocalIdentifier(ServiceBase):
    """StopRoutineByLocalIdentifier service (0x32)."""
    
    SERVICE_ID = SERVICE_STOP_ROUTINE_BY_LOCAL_IDENTIFIER
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        routine_id_echo: int
    
    @classmethod
    def make_request(cls, routine_id: int) -> Request:
        """
        Create a StopRoutineByLocalIdentifier request.
        
        Args:
            routine_id: Routine ID (2 bytes, big-endian)
            
        Returns:
            Request object
        """
        routine_id_high = (routine_id >> 8) & 0xFF
        routine_id_low = routine_id & 0xFF
        data = bytes([routine_id_high, routine_id_low])
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'StopRoutineByLocalIdentifier.ServiceData':
        """
        Interpret a StopRoutineByLocalIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 2:
            raise ValueError("Invalid response data length: must be at least 2 bytes")
        
        routine_id_high = response.data[0]
        routine_id_low = response.data[1]
        routine_id_echo = (routine_id_high << 8) | routine_id_low
        
        return cls.ServiceData(routine_id_echo=routine_id_echo)


class RequestRoutineResultsByLocalIdentifier(ServiceBase):
    """RequestRoutineResultsByLocalIdentifier service (0x33)."""
    
    SERVICE_ID = SERVICE_REQUEST_ROUTINE_RESULTS_BY_LOCAL_IDENTIFIER
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        routine_id_echo: int
        routine_results: bytes
    
    @classmethod
    def make_request(cls, routine_id: int) -> Request:
        """
        Create a RequestRoutineResultsByLocalIdentifier request.
        
        Args:
            routine_id: Routine ID (2 bytes, big-endian)
            
        Returns:
            Request object
        """
        routine_id_high = (routine_id >> 8) & 0xFF
        routine_id_low = routine_id & 0xFF
        data = bytes([routine_id_high, routine_id_low])
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'RequestRoutineResultsByLocalIdentifier.ServiceData':
        """
        Interpret a RequestRoutineResultsByLocalIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 2:
            raise ValueError("Invalid response data length: must be at least 2 bytes")
        
        routine_id_high = response.data[0]
        routine_id_low = response.data[1]
        routine_id_echo = (routine_id_high << 8) | routine_id_low
        routine_results = response.data[2:] if len(response.data) > 2 else b''
        
        return cls.ServiceData(
            routine_id_echo=routine_id_echo,
            routine_results=routine_results
        )


class StartRoutineByAddress(ServiceBase):
    """StartRoutineByAddress service (0x38)."""
    
    SERVICE_ID = SERVICE_START_ROUTINE_BY_ADDRESS
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_address_echo: int
    
    @classmethod
    def make_request(
        cls,
        memory_address: int,
        routine_control_option_record: Optional[bytes] = None
    ) -> Request:
        """
        Create a StartRoutineByAddress request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            routine_control_option_record: Optional routine control option record bytes
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        data = bytes([memory_address_high, memory_address_middle, memory_address_low])
        if routine_control_option_record:
            data += routine_control_option_record
        
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'StartRoutineByAddress.ServiceData':
        """
        Interpret a StartRoutineByAddress response.
        
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
            raise ValueError("Invalid response data length: must be at least 3 bytes")
        
        memory_address_high = response.data[0]
        memory_address_middle = response.data[1]
        memory_address_low = response.data[2]
        memory_address_echo = (memory_address_high << 16) | (memory_address_middle << 8) | memory_address_low
        
        return cls.ServiceData(memory_address_echo=memory_address_echo)


class StopRoutineByAddress(ServiceBase):
    """StopRoutineByAddress service (0x39)."""
    
    SERVICE_ID = SERVICE_STOP_ROUTINE_BY_ADDRESS
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_address_echo: int
    
    @classmethod
    def make_request(cls, memory_address: int) -> Request:
        """
        Create a StopRoutineByAddress request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        data = bytes([memory_address_high, memory_address_middle, memory_address_low])
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'StopRoutineByAddress.ServiceData':
        """
        Interpret a StopRoutineByAddress response.
        
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
            raise ValueError("Invalid response data length: must be at least 3 bytes")
        
        memory_address_high = response.data[0]
        memory_address_middle = response.data[1]
        memory_address_low = response.data[2]
        memory_address_echo = (memory_address_high << 16) | (memory_address_middle << 8) | memory_address_low
        
        return cls.ServiceData(memory_address_echo=memory_address_echo)


class RequestRoutineResultsByAddress(ServiceBase):
    """RequestRoutineResultsByAddress service (0x3A)."""
    
    SERVICE_ID = SERVICE_REQUEST_ROUTINE_RESULTS_BY_ADDRESS
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_address_echo: int
        routine_results: bytes
    
    @classmethod
    def make_request(cls, memory_address: int) -> Request:
        """
        Create a RequestRoutineResultsByAddress request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        data = bytes([memory_address_high, memory_address_middle, memory_address_low])
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'RequestRoutineResultsByAddress.ServiceData':
        """
        Interpret a RequestRoutineResultsByAddress response.
        
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
            raise ValueError("Invalid response data length: must be at least 3 bytes")
        
        memory_address_high = response.data[0]
        memory_address_middle = response.data[1]
        memory_address_low = response.data[2]
        memory_address_echo = (memory_address_high << 16) | (memory_address_middle << 8) | memory_address_low
        routine_results = response.data[3:] if len(response.data) > 3 else b''
        
        return cls.ServiceData(
            memory_address_echo=memory_address_echo,
            routine_results=routine_results
        )


# ============================================================================
# Upload/Download Services
# ============================================================================

class RequestDownload(ServiceBase):
    """RequestDownload service (0x34)."""
    
    SERVICE_ID = SERVICE_REQUEST_DOWNLOAD
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_address_echo: int
        memory_size_echo: int
        max_number_of_block_length: Optional[int] = None
    
    @classmethod
    def make_request(
        cls,
        memory_address: int,
        memory_size: int,
        compression_method: Optional[int] = None,
        encryption_method: Optional[int] = None
    ) -> Request:
        """
        Create a RequestDownload request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Memory size (24-bit, 3 bytes)
            compression_method: Optional compression method (1 byte)
            encryption_method: Optional encryption method (1 byte)
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        # Extract size bytes (High, Middle, Low)
        memory_size_high = (memory_size >> 16) & 0xFF
        memory_size_middle = (memory_size >> 8) & 0xFF
        memory_size_low = memory_size & 0xFF
        
        data = bytes([
            memory_address_high,
            memory_address_middle,
            memory_address_low,
            memory_size_high,
            memory_size_middle,
            memory_size_low
        ])
        
        if compression_method is not None:
            data += bytes([compression_method])
        if encryption_method is not None:
            data += bytes([encryption_method])
        
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'RequestDownload.ServiceData':
        """
        Interpret a RequestDownload response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 6:
            raise ValueError("Invalid response data length: must be at least 6 bytes")
        
        # Parse memory address echo
        memory_address_high = response.data[0]
        memory_address_middle = response.data[1]
        memory_address_low = response.data[2]
        memory_address_echo = (memory_address_high << 16) | (memory_address_middle << 8) | memory_address_low
        
        # Parse memory size echo
        memory_size_high = response.data[3]
        memory_size_middle = response.data[4]
        memory_size_low = response.data[5]
        memory_size_echo = (memory_size_high << 16) | (memory_size_middle << 8) | memory_size_low
        
        max_number_of_block_length = None
        if len(response.data) >= 7:
            max_number_of_block_length = response.data[6]
        
        return cls.ServiceData(
            memory_address_echo=memory_address_echo,
            memory_size_echo=memory_size_echo,
            max_number_of_block_length=max_number_of_block_length
        )


class RequestUpload(ServiceBase):
    """RequestUpload service (0x35)."""
    
    SERVICE_ID = SERVICE_REQUEST_UPLOAD
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        memory_address_echo: int
        memory_size_echo: int
        max_number_of_block_length: Optional[int] = None
    
    @classmethod
    def make_request(
        cls,
        memory_address: int,
        memory_size: int,
        compression_method: Optional[int] = None,
        encryption_method: Optional[int] = None
    ) -> Request:
        """
        Create a RequestUpload request.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Memory size (24-bit, 3 bytes)
            compression_method: Optional compression method (1 byte)
            encryption_method: Optional encryption method (1 byte)
            
        Returns:
            Request object
        """
        # Extract address bytes (High, Middle, Low)
        memory_address_high = (memory_address >> 16) & 0xFF
        memory_address_middle = (memory_address >> 8) & 0xFF
        memory_address_low = memory_address & 0xFF
        
        # Extract size bytes (High, Middle, Low)
        memory_size_high = (memory_size >> 16) & 0xFF
        memory_size_middle = (memory_size >> 8) & 0xFF
        memory_size_low = memory_size & 0xFF
        
        data = bytes([
            memory_address_high,
            memory_address_middle,
            memory_address_low,
            memory_size_high,
            memory_size_middle,
            memory_size_low
        ])
        
        if compression_method is not None:
            data += bytes([compression_method])
        if encryption_method is not None:
            data += bytes([encryption_method])
        
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'RequestUpload.ServiceData':
        """
        Interpret a RequestUpload response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 6:
            raise ValueError("Invalid response data length: must be at least 6 bytes")
        
        # Parse memory address echo
        memory_address_high = response.data[0]
        memory_address_middle = response.data[1]
        memory_address_low = response.data[2]
        memory_address_echo = (memory_address_high << 16) | (memory_address_middle << 8) | memory_address_low
        
        # Parse memory size echo
        memory_size_high = response.data[3]
        memory_size_middle = response.data[4]
        memory_size_low = response.data[5]
        memory_size_echo = (memory_size_high << 16) | (memory_size_middle << 8) | memory_size_low
        
        max_number_of_block_length = None
        if len(response.data) >= 7:
            max_number_of_block_length = response.data[6]
        
        return cls.ServiceData(
            memory_address_echo=memory_address_echo,
            memory_size_echo=memory_size_echo,
            max_number_of_block_length=max_number_of_block_length
        )


class TransferData(ServiceBase):
    """TransferData service (0x36)."""
    
    SERVICE_ID = SERVICE_TRANSFER_DATA
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        block_sequence_number_echo: int
        transfer_response_parameter_record: Optional[bytes] = None
    
    @classmethod
    def make_request(
        cls,
        block_sequence_number: int,
        transfer_request_parameter_record: bytes
    ) -> Request:
        """
        Create a TransferData request.
        
        Args:
            block_sequence_number: Block sequence number (1 byte)
            transfer_request_parameter_record: Transfer request parameter record bytes
            
        Returns:
            Request object
        """
        data = bytes([block_sequence_number]) + transfer_request_parameter_record
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'TransferData.ServiceData':
        """
        Interpret a TransferData response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        block_sequence_number_echo = response.data[0]
        transfer_response_parameter_record = response.data[1:] if len(response.data) > 1 else None
        
        return cls.ServiceData(
            block_sequence_number_echo=block_sequence_number_echo,
            transfer_response_parameter_record=transfer_response_parameter_record
        )


class RequestTransferExit(ServiceBase):
    """RequestTransferExit service (0x37)."""
    
    SERVICE_ID = SERVICE_REQUEST_TRANSFER_EXIT
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        transfer_response_parameter_record: Optional[bytes] = None
    
    @classmethod
    def make_request(
        cls,
        transfer_request_parameter_record: Optional[bytes] = None
    ) -> Request:
        """
        Create a RequestTransferExit request.
        
        Args:
            transfer_request_parameter_record: Optional transfer request parameter record bytes
            
        Returns:
            Request object
        """
        data = transfer_request_parameter_record if transfer_request_parameter_record else b''
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'RequestTransferExit.ServiceData':
        """
        Interpret a RequestTransferExit response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        transfer_response_parameter_record = response.data if len(response.data) > 0 else None
        
        return cls.ServiceData(
            transfer_response_parameter_record=transfer_response_parameter_record
        )


# ============================================================================
# Security Services
# ============================================================================

class SecurityAccess(ServiceBase):
    """SecurityAccess service (0x27)."""
    
    SERVICE_ID = SERVICE_SECURITY_ACCESS
    
    class AccessType:
        """Security access type constants."""
        REQUEST_SEED = 0x01  # Request seed
        SEND_KEY = 0x02  # Send key
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        access_type_echo: int
        security_access_data: Optional[bytes] = None
    
    @classmethod
    def make_request(
        cls,
        access_type: int,
        security_access_data: Optional[bytes] = None
    ) -> Request:
        """
        Create a SecurityAccess request.
        
        Args:
            access_type: Access type (0x01=request seed, 0x02=send key)
            security_access_data: Optional security access data (e.g., key for send key)
            
        Returns:
            Request object
        """
        data = bytes([access_type])
        if security_access_data:
            data += security_access_data
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'SecurityAccess.ServiceData':
        """
        Interpret a SecurityAccess response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        access_type_echo = response.data[0]
        security_access_data = response.data[1:] if len(response.data) > 1 else None
        
        return cls.ServiceData(
            access_type_echo=access_type_echo,
            security_access_data=security_access_data
        )


# ============================================================================
# Other Services
# ============================================================================

class ReadEcuIdentification(ServiceBase):
    """ReadEcuIdentification service (0x1A)."""
    
    SERVICE_ID = SERVICE_READ_ECU_IDENTIFICATION
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        ecu_identification_data: bytes
    
    @classmethod
    def make_request(cls, ecu_identification_option: Optional[int] = None) -> Request:
        """
        Create a ReadEcuIdentification request.
        
        Args:
            ecu_identification_option: Optional ECU identification option byte
            
        Returns:
            Request object
        """
        data = bytes([ecu_identification_option]) if ecu_identification_option is not None else b''
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'ReadEcuIdentification.ServiceData':
        """
        Interpret a ReadEcuIdentification response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        return cls.ServiceData(ecu_identification_data=response.data)


class DynamicallyDefineLocalIdentifier(ServiceBase):
    """DynamicallyDefineLocalIdentifier service (0x2C)."""
    
    SERVICE_ID = SERVICE_DYNAMICALLY_DEFINE_LOCAL_IDENTIFIER
    
    class SubFunction:
        """Sub-function constants."""
        DEFINE_BY_IDENTIFIER = 0x01
        DEFINE_BY_MEMORY_ADDRESS = 0x02
        CLEAR_DYNAMICALLY_DEFINED_LOCAL_IDENTIFIER = 0x03
    
    @dataclass
    class ServiceData:
        """Parsed service data from response."""
        sub_function_echo: int
    
    @classmethod
    def make_request(
        cls,
        sub_function: int,
        definition_record: bytes
    ) -> Request:
        """
        Create a DynamicallyDefineLocalIdentifier request.
        
        Args:
            sub_function: Sub-function (0x01=define by identifier, 0x02=define by memory address, 0x03=clear)
            definition_record: Definition record bytes
            
        Returns:
            Request object
        """
        data = bytes([sub_function]) + definition_record
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> 'DynamicallyDefineLocalIdentifier.ServiceData':
        """
        Interpret a DynamicallyDefineLocalIdentifier response.
        
        Args:
            response: Response object
            
        Returns:
            ServiceData with parsed response data
            
        Raises:
            ValueError: If response data is invalid
        """
        if not response.is_positive():
            raise ValueError("Response is not positive")
        
        if len(response.data) < 1:
            raise ValueError("Invalid response data length: must be at least 1 byte")
        
        return cls.ServiceData(sub_function_echo=response.data[0])


class EscCode(ServiceBase):
    """EscCode service (0x80) - KWP2000 specific, not part of standard diagnostic services."""
    
    SERVICE_ID = SERVICE_ESC_CODE
    POSITIVE_RESPONSE_SERVICE_ID = 0xC0  # EscCodePositiveResponse
    
    @classmethod
    def make_request(cls, esc_code_data: Optional[bytes] = None) -> Request:
        """
        Create an EscCode request.
        
        Args:
            esc_code_data: Optional ESC code data bytes
            
        Returns:
            Request object
        """
        data = esc_code_data if esc_code_data else b''
        return Request(cls.SERVICE_ID, data)
    
    @classmethod
    def interpret_response(cls, response: Response) -> dict:
        """
        Interpret an EscCode response.
        
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

