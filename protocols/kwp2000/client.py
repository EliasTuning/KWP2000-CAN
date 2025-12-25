"""Client class for KWP2000 communication."""
from typing import Optional

from .request import Request
from .response import Response
from .exceptions import TimeoutException, NegativeResponseException
from .constants import TimingParameters
from .transport import Transport
from . import services


class KWP2000Client:
    """
    High-level client for KWP2000 communication.
    
    Provides convenient methods for common operations.
    
    Usage:
        with KWP2000Client(transport) as client:
            response = client.start_routine(routine_id=0x1234)
    """
    
    def __init__(self, transport: Transport):
        """
        Initialize client with a transport.
        
        Args:
            transport: Transport instance to use
        """
        self.transport = transport
        self._is_open = False
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def open(self) -> None:
        """Open the transport connection."""
        self.transport.open()
        self._is_open = True
    
    def close(self) -> None:
        """Close the transport connection."""
        self.transport.close()
        self._is_open = False
    
    def send_request(self, request: Request, timeout: float = 1.0) -> Response:
        """
        Send a request and wait for response.
        
        Args:
            request: Request object to send
            timeout: Timeout in seconds
            
        Returns:
            Response object
            
        Raises:
            TimeoutException: If timeout occurs
            NegativeResponseException: If negative response received
        """
        if not self._is_open:
            raise RuntimeError("Client not open")
        
        # Send request
        # For TP20 transport, send only service data (service ID + data)
        # TP20 handles framing, so KWP2000 headers are not needed
        payload = request.get_data()
        self.transport.send(payload)
        
        # Wait for response
        response_payload = self.transport.wait_frame(timeout=timeout)
        if response_payload is None:
            raise TimeoutException("Timeout waiting for response")
        
        # Parse response
        try:
            response = Response.from_payload(response_payload)
        except NegativeResponseException:
            raise  # Re-raise negative responses
        
        return response
    
    def start_routine(
        self,
        routine_id: int,
        control_type: int = services.RoutineControl.ControlType.startRoutine,
        timeout: float = 1.0
    ) -> services.RoutineControl.ServiceData:
        """
        Start a routine.
        
        Args:
            routine_id: Routine ID
            control_type: Control type (default: startRoutine)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information
            
        Raises:
            TimeoutException: If timeout occurs
            NegativeResponseException: If negative response received
            ValueError: If response is invalid
        """
        request = services.RoutineControl.make_request(
            control_type=control_type,
            routine_id=routine_id
        )
        response = self.send_request(request, timeout=timeout)
        
        # Interpret response
        service_data = services.RoutineControl.interpret_response(response)
        
        # Validate echo values
        if service_data.control_type_echo != control_type:
            raise ValueError(f"Control type echo mismatch: expected {control_type}, got {service_data.control_type_echo}")
        if service_data.routine_id_echo != routine_id:
            raise ValueError(f"Routine ID echo mismatch: expected {routine_id:04X}, got {service_data.routine_id_echo:04X}")
        
        return service_data
    
    def stop_routine(
        self,
        routine_id: int,
        timeout: float = 1.0
    ) -> services.RoutineControl.ServiceData:
        """
        Stop a routine.
        
        Args:
            routine_id: Routine ID
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information
        """
        return self.start_routine(
            routine_id=routine_id,
            control_type=services.RoutineControl.ControlType.stopRoutine,
            timeout=timeout
        )
    
    def request_routine_results(
        self,
        routine_id: int,
        timeout: float = 1.0
    ) -> services.RoutineControl.ServiceData:
        """
        Request routine results.
        
        Args:
            routine_id: Routine ID
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information
        """
        return self.start_routine(
            routine_id=routine_id,
            control_type=services.RoutineControl.ControlType.requestRoutineResults,
            timeout=timeout
        )
    
    def start_communication(
        self,
        key_bytes: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> dict:
        """
        Start communication session.
        
        Args:
            key_bytes: Optional key bytes
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data
        """
        request = services.StartCommunication.make_request(key_bytes=key_bytes)
        response = self.send_request(request, timeout=timeout)
        return services.StartCommunication.interpret_response(response)
    
    def stop_communication(self, timeout: float = 1.0) -> dict:
        """
        Stop communication session.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data
        """
        request = services.StopCommunication.make_request()
        response = self.send_request(request, timeout=timeout)
        return services.StopCommunication.interpret_response(response)
    
    def ecu_reset(
        self,
        reset_type: int,
        timeout: float = 1.0
    ) -> dict:
        """
        Reset ECU.
        
        Args:
            reset_type: Reset type
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data
        """
        request = services.ECUReset.make_request(reset_type=reset_type)
        response = self.send_request(request, timeout=timeout)
        return services.ECUReset.interpret_response(response)
    
    def tester_present(
        self,
        response_required: int = services.TesterPresent.ResponseRequired.YES,
        timeout: float = 1.0
    ) -> dict:
        """
        Send TesterPresent message to keep the diagnostic session alive.
        
        According to KWP2000 specification:
        - Byte #1: Service ID = 0x3E (TP)
        - Byte #2: responseRequired (0x01 = yes, 0x02 = no)
        
        Positive Response:
        - Byte #1: Service ID = 0x7E (TPPR)
        - No data bytes
        
        Args:
            response_required: Response required flag (0x01 = yes, 0x02 = no, default: 0x01)
            timeout: Timeout in seconds (only used if response_required = YES)
            
        Returns:
            Dictionary with response data (empty for positive response)
            
        Raises:
            TimeoutException: If timeout occurs and response was required
            NegativeResponseException: If negative response received
        """
        request = services.TesterPresent.make_request(response_required=response_required)
        
        # If response is not required, send and don't wait
        if response_required == services.TesterPresent.ResponseRequired.NO:
            # Just send the request without waiting for response
            payload = request.get_data()
            self.transport.send(payload)
            return {}
        
        # If response is required, send and wait for response
        response = self.send_request(request, timeout=timeout)
        return services.TesterPresent.interpret_response(response)
    
    def send_data(
        self,
        data: bytes,
        timeout: float = 1.0
    ) -> dict:
        """
        Send data.
        
        Args:
            data: Data bytes to send
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data
        """
        request = services.SendData.make_request(data=data)
        response = self.send_request(request, timeout=timeout)
        return services.SendData.interpret_response(response)
    
    def access_timing_parameter(
        self,
        timing_parameters: Optional[TimingParameters] = None,
        timing_parameter_id: int = services.AccessTimingParameter.TPI_SP,
        timeout: float = 1.0
    ) -> services.AccessTimingParameter.ServiceData:
        """
        Access timing parameters.
        
        According to KWP2000 ISO 14230-3 specification:
        - TimingParameterIdentifier = 0x03 (TPI_SP)
        - P2min = 0x32 (25 ms with 0.5 ms resolution)
          P2 = Zeit zwischen Request und Antworttelegramm bzw. Zeit zwischen 2 Antworttelegrammen (25-50ms)
        - P2max = 0x02 (50 ms with 25 ms resolution)
        - P3min = 0x6E (55 ms with 0.5 ms resolution)
          P3 = Zeit zwischen Antworttelegrammende und neuem Request (55-µms)
        - P3max = 0x14 (5000 ms with 250 ms resolution)
        - P4min = 0x0A (5 ms with 0.5 ms resolution)
          P4 = Bytezwischenzeit des Requesttelegramms (0-20ms)
        
        Note: P1 = Bytezwischenzeit des Antworttelegramms (0-20ms) is not part of this service.
        
        Args:
            timing_parameters: TimingParameters instance (e.g., TIMING_PARAMETER_STANDARD or TIMING_PARAMETER_MINIMAL).
                               If provided, individual p2min/p2max/p3min/p3max/p4min parameters are ignored.
            timing_parameter_id: Timing parameter identifier (default: 0x03 = TPI_SP)
            p2min: P2min value - Minimum Zeit zwischen Request und Antworttelegramm (default: 0x32 = 25 ms)
                   Ignored if timing_parameters is provided.
            p2max: P2max value - Maximum Zeit zwischen Request und Antworttelegramm (default: 0x02 = 50 ms)
                   Ignored if timing_parameters is provided.
            p3min: P3min value - Minimum Zeit zwischen Antworttelegrammende und neuem Request (default: 0x6E = 55 ms)
                   Ignored if timing_parameters is provided.
            p3max: P3max value - Maximum Zeit zwischen Antworttelegrammende und neuem Request (default: 0x14 = 5000 ms)
                   Ignored if timing_parameters is provided.
            p4min: P4min value - Bytezwischenzeit des Requesttelegramms (default: 0x0A = 5 ms)
                   Ignored if timing_parameters is provided.
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data containing:
                - timing_parameter_id: Echo of the timing parameter identifier
                - timing_parameters: TimingParameters object with parsed timing values
        
        Example:
            from kwp2000.constants import TIMING_PARAMETER_STANDARD
            
            # Using dataclass instance
            client.access_timing_parameter(TIMING_PARAMETER_STANDARD)
            
            # Using individual parameters (backward compatible)
            client.access_timing_parameter(p2min=0x32, p2max=0x02, ...)
        """

        request = services.AccessTimingParameter.make_request(
            timing_parameter_id=timing_parameter_id,
            p2min=timing_parameters.p2min,
            p2max=timing_parameters.p2max,
            p3min=timing_parameters.p3min,
            p3max=timing_parameters.p3max,
            p4min=timing_parameters.p4min
        )

        response = self.send_request(request, timeout=timeout)
        return services.AccessTimingParameter.interpret_response(response)
    
    def startDiagnosticSession(
        self,
        diagnostic_mode: Optional[int] = None,
        baudrate_identifier: Optional[int] = None,
        session_type: Optional[int] = None,  # Backward compatibility alias
        timeout: float = 1.0
    ) -> dict:
        """
        Start diagnostic session.
        
        Args:
            diagnostic_mode: Diagnostic mode (0x81=OBD2, 0x85=ECU Programming, 0x86=ECU Development)
            baudrate_identifier: Optional baudrate identifier (0x01=9600, 0x02=19200, etc.)
            session_type: Backward compatibility alias for diagnostic_mode
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with parsed response data containing:
                - diagnostic_mode: Echo of the requested diagnostic mode
                - session_type_echo: Backward compatibility alias for diagnostic_mode
                - baudrate_identifier: Echo of the requested baudrate identifier (if present)
        """
        request = services.StartDiagnosticSession.make_request(
            diagnostic_mode=diagnostic_mode,
            baudrate_identifier=baudrate_identifier,
            session_type=session_type
        )
        response = self.send_request(request, timeout=timeout)
        return services.StartDiagnosticSession.interpret_response(response)
    
    def readDataByLocalIdentifier(
        self,
        local_identifier: int,
        timeout: float = 1.0
    ) -> dict:
        """
        Read data by local identifier.
        
        Args:
            local_identifier: Local identifier to read
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data containing:
                - local_identifier_echo: Echo of the requested local identifier
                - data: The data bytes read
        """
        request = services.ReadDataByLocalIdentifier.make_request(
            local_identifier=local_identifier
        )
        response = self.send_request(request, timeout=timeout)
        return services.ReadDataByLocalIdentifier.interpret_response(response)
    
    def read_data_by_identifier(
        self,
        local_identifier: int,
        timeout: float = 1.0
    ) -> dict:
        """
        Read data by local identifier (alias for readDataByLocalIdentifier).
        
        Args:
            local_identifier: Local identifier to read
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data containing:
                - local_identifier_echo: Echo of the requested local identifier
                - data: The data bytes read
        """
        return self.readDataByLocalIdentifier(local_identifier, timeout)
    
    def readMemoryByAddress(
        self,
        memory_address: int,
        memory_size: int,
        transmission_mode: Optional[int] = None,
        maximum_number_of_responses_to_send: Optional[int] = None,
        timeout: float = 1.0
    ) -> services.ReadMemoryByAddress.ServiceData:
        """
        Read memory by address.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Number of bytes to read (1 byte)
            transmission_mode: Optional transmission mode (0x01=single, 0x02=slow, 0x03=medium, 0x04=fast, 0x05=stop)
            maximum_number_of_responses_to_send: Optional maximum number of responses (only if transmission_mode is provided)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information containing:
                - record_values: The memory data read (bytes)
                - memory_address_echo: Echo of the requested memory address (24-bit)
            
        Raises:
            TimeoutException: If timeout occurs
            NegativeResponseException: If negative response received
            ValueError: If response is invalid
        """
        request = services.ReadMemoryByAddress.make_request(
            memory_address=memory_address,
            memory_size=memory_size,
            transmission_mode=transmission_mode,
            maximum_number_of_responses_to_send=maximum_number_of_responses_to_send
        )
        response = self.send_request(request, timeout=timeout)
        return services.ReadMemoryByAddress.interpret_response(response)
    
    def readMemoryByAddress2(
        self,
        memory_address: int,
        memory_type: int,
        memory_size: int,
        timeout: float = 1.0
    ) -> services.ReadMemoryByAddress2.ServiceData:
        """
        Read memory by address (variant 2 with memory type).
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_type: Memory type (1 byte)
            memory_size: Number of bytes to read (1 byte)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information containing:
                - record_values: The memory data read (bytes)
            
        Raises:
            TimeoutException: If timeout occurs
            NegativeResponseException: If negative response received
            ValueError: If response is invalid
        """
        request = services.ReadMemoryByAddress2.make_request(
            memory_address=memory_address,
            memory_type=memory_type,
            memory_size=memory_size
        )
        response = self.send_request(request, timeout=timeout)
        return services.ReadMemoryByAddress2.interpret_response(response)
    
    def stop_diagnostic_session(self, timeout: float = 1.0) -> dict:
        """
        Stop diagnostic session.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with parsed response data
        """
        request = services.StopDiagnosticSession.make_request()
        response = self.send_request(request, timeout=timeout)
        return services.StopDiagnosticSession.interpret_response(response)
    
    def read_freeze_frame_data(
        self,
        freeze_frame_number: int,
        timeout: float = 1.0
    ) -> services.ReadFreezeFrameData.ServiceData:
        """
        Read freeze frame data.
        
        Args:
            freeze_frame_number: Freeze frame number
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.ReadFreezeFrameData.make_request(freeze_frame_number=freeze_frame_number)
        response = self.send_request(request, timeout=timeout)
        return services.ReadFreezeFrameData.interpret_response(response)
    
    def read_diagnostic_trouble_codes(
        self,
        timeout: float = 1.0
    ) -> services.ReadDiagnosticTroubleCodes.ServiceData:
        """
        Read diagnostic trouble codes.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed DTCs
        """
        request = services.ReadDiagnosticTroubleCodes.make_request()
        response = self.send_request(request, timeout=timeout)
        return services.ReadDiagnosticTroubleCodes.interpret_response(response)
    
    def clear_diagnostic_information(
        self,
        group_of_dtc: int,
        timeout: float = 1.0
    ) -> dict:
        """
        Clear diagnostic information.
        
        Args:
            group_of_dtc: Group of DTC to clear
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with parsed response data
        """
        request = services.ClearDiagnosticInformation.make_request(group_of_dtc=group_of_dtc)
        response = self.send_request(request, timeout=timeout)
        return services.ClearDiagnosticInformation.interpret_response(response)
    
    def read_status_of_diagnostic_trouble_codes(
        self,
        timeout: float = 1.0
    ) -> services.ReadStatusOfDiagnosticTroubleCodes.ServiceData:
        """
        Read status of diagnostic trouble codes.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with status byte
        """
        request = services.ReadStatusOfDiagnosticTroubleCodes.make_request()
        response = self.send_request(request, timeout=timeout)
        return services.ReadStatusOfDiagnosticTroubleCodes.interpret_response(response)
    
    def read_diagnostic_trouble_codes_by_status(
        self,
        status_mask: int,
        timeout: float = 1.0
    ) -> services.ReadDiagnosticTroubleCodesByStatus.ServiceData:
        """
        Read diagnostic trouble codes by status.
        
        Args:
            status_mask: Status mask byte
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed DTCs
        """
        request = services.ReadDiagnosticTroubleCodesByStatus.make_request(status_mask=status_mask)
        response = self.send_request(request, timeout=timeout)
        return services.ReadDiagnosticTroubleCodesByStatus.interpret_response(response)
    
    def read_data_by_common_identifier(
        self,
        common_identifier: int,
        timeout: float = 1.0
    ) -> services.ReadDataByCommonIdentifier.ServiceData:
        """
        Read data by common identifier.
        
        Args:
            common_identifier: Common identifier to read
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.ReadDataByCommonIdentifier.make_request(common_identifier=common_identifier)
        response = self.send_request(request, timeout=timeout)
        return services.ReadDataByCommonIdentifier.interpret_response(response)
    
    def set_data_rates(
        self,
        data_rate_identifier: int,
        timeout: float = 1.0
    ) -> services.SetDataRates.ServiceData:
        """
        Set data rates.
        
        Args:
            data_rate_identifier: Data rate identifier
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.SetDataRates.make_request(data_rate_identifier=data_rate_identifier)
        response = self.send_request(request, timeout=timeout)
        return services.SetDataRates.interpret_response(response)
    
    def write_data_by_common_identifier(
        self,
        common_identifier: int,
        data: bytes,
        timeout: float = 1.0
    ) -> services.WriteDataByCommonIdentifier.ServiceData:
        """
        Write data by common identifier.
        
        Args:
            common_identifier: Common identifier
            data: Data bytes to write
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.WriteDataByCommonIdentifier.make_request(
            common_identifier=common_identifier,
            data=data
        )
        response = self.send_request(request, timeout=timeout)
        return services.WriteDataByCommonIdentifier.interpret_response(response)
    
    def write_data_by_local_identifier(
        self,
        local_identifier: int,
        data: bytes,
        timeout: float = 1.0
    ) -> services.WriteDataByLocalIdentifier.ServiceData:
        """
        Write data by local identifier.
        
        Args:
            local_identifier: Local identifier
            data: Data bytes to write
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.WriteDataByLocalIdentifier.make_request(
            local_identifier=local_identifier,
            data=data
        )
        response = self.send_request(request, timeout=timeout)
        return services.WriteDataByLocalIdentifier.interpret_response(response)
    
    def write_memory_by_address(
        self,
        memory_address: int,
        memory_size: int,
        data: bytes,
        timeout: float = 1.0
    ) -> services.WriteMemoryByAddress.ServiceData:
        """
        Write memory by address.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Number of bytes to write
            data: Data bytes to write
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.WriteMemoryByAddress.make_request(
            memory_address=memory_address,
            memory_size=memory_size,
            data=data
        )
        response = self.send_request(request, timeout=timeout)
        return services.WriteMemoryByAddress.interpret_response(response)
    
    def input_output_control_by_common_identifier(
        self,
        common_identifier: int,
        control_parameter: int,
        control_state: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> services.InputOutputControlByCommonIdentifier.ServiceData:
        """
        Input/output control by common identifier.
        
        Args:
            common_identifier: Common identifier
            control_parameter: Control parameter
            control_state: Optional control state bytes
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.InputOutputControlByCommonIdentifier.make_request(
            common_identifier=common_identifier,
            control_parameter=control_parameter,
            control_state=control_state
        )
        response = self.send_request(request, timeout=timeout)
        return services.InputOutputControlByCommonIdentifier.interpret_response(response)
    
    def input_output_control_by_local_identifier(
        self,
        local_identifier: int,
        control_parameter: int,
        control_state: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> services.InputOutputControlByLocalIdentifier.ServiceData:
        """
        Input/output control by local identifier.
        
        Args:
            local_identifier: Local identifier
            control_parameter: Control parameter
            control_state: Optional control state bytes
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.InputOutputControlByLocalIdentifier.make_request(
            local_identifier=local_identifier,
            control_parameter=control_parameter,
            control_state=control_state
        )
        response = self.send_request(request, timeout=timeout)
        return services.InputOutputControlByLocalIdentifier.interpret_response(response)
    
    def stop_routine_by_local_identifier(
        self,
        routine_id: int,
        timeout: float = 1.0
    ) -> services.StopRoutineByLocalIdentifier.ServiceData:
        """
        Stop routine by local identifier.
        
        Args:
            routine_id: Routine ID
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.StopRoutineByLocalIdentifier.make_request(routine_id=routine_id)
        response = self.send_request(request, timeout=timeout)
        return services.StopRoutineByLocalIdentifier.interpret_response(response)
    
    def request_routine_results_by_local_identifier(
        self,
        routine_id: int,
        timeout: float = 1.0
    ) -> services.RequestRoutineResultsByLocalIdentifier.ServiceData:
        """
        Request routine results by local identifier.
        
        Args:
            routine_id: Routine ID
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.RequestRoutineResultsByLocalIdentifier.make_request(routine_id=routine_id)
        response = self.send_request(request, timeout=timeout)
        return services.RequestRoutineResultsByLocalIdentifier.interpret_response(response)
    
    def start_routine_by_address(
        self,
        memory_address: int,
        routine_control_option_record: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> services.StartRoutineByAddress.ServiceData:
        """
        Start routine by address.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            routine_control_option_record: Optional routine control option record bytes
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.StartRoutineByAddress.make_request(
            memory_address=memory_address,
            routine_control_option_record=routine_control_option_record
        )
        response = self.send_request(request, timeout=timeout)
        return services.StartRoutineByAddress.interpret_response(response)
    
    def stop_routine_by_address(
        self,
        memory_address: int,
        timeout: float = 1.0
    ) -> services.StopRoutineByAddress.ServiceData:
        """
        Stop routine by address.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.StopRoutineByAddress.make_request(memory_address=memory_address)
        response = self.send_request(request, timeout=timeout)
        return services.StopRoutineByAddress.interpret_response(response)
    
    def request_routine_results_by_address(
        self,
        memory_address: int,
        timeout: float = 1.0
    ) -> services.RequestRoutineResultsByAddress.ServiceData:
        """
        Request routine results by address.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.RequestRoutineResultsByAddress.make_request(memory_address=memory_address)
        response = self.send_request(request, timeout=timeout)
        return services.RequestRoutineResultsByAddress.interpret_response(response)
    
    def request_download(
        self,
        memory_address: int,
        memory_size: int,
        compression_method: Optional[int] = None,
        encryption_method: Optional[int] = None,
        timeout: float = 1.0
    ) -> services.RequestDownload.ServiceData:
        """
        Request download.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Memory size (24-bit, 3 bytes)
            compression_method: Optional compression method
            encryption_method: Optional encryption method
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.RequestDownload.make_request(
            memory_address=memory_address,
            memory_size=memory_size,
            compression_method=compression_method,
            encryption_method=encryption_method
        )
        response = self.send_request(request, timeout=timeout)
        return services.RequestDownload.interpret_response(response)
    
    def request_upload(
        self,
        memory_address: int,
        memory_size: int,
        compression_method: Optional[int] = None,
        encryption_method: Optional[int] = None,
        timeout: float = 1.0
    ) -> services.RequestUpload.ServiceData:
        """
        Request upload.
        
        Args:
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Memory size (24-bit, 3 bytes)
            compression_method: Optional compression method
            encryption_method: Optional encryption method
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.RequestUpload.make_request(
            memory_address=memory_address,
            memory_size=memory_size,
            compression_method=compression_method,
            encryption_method=encryption_method
        )
        response = self.send_request(request, timeout=timeout)
        return services.RequestUpload.interpret_response(response)
    
    def transfer_data(
        self,
        block_sequence_number: int,
        transfer_request_parameter_record: bytes,
        timeout: float = 1.0
    ) -> services.TransferData.ServiceData:
        """
        Transfer data.
        
        Args:
            block_sequence_number: Block sequence number
            transfer_request_parameter_record: Transfer request parameter record bytes
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.TransferData.make_request(
            block_sequence_number=block_sequence_number,
            transfer_request_parameter_record=transfer_request_parameter_record
        )
        response = self.send_request(request, timeout=timeout)
        return services.TransferData.interpret_response(response)
    
    def request_transfer_exit(
        self,
        transfer_request_parameter_record: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> services.RequestTransferExit.ServiceData:
        """
        Request transfer exit.
        
        Args:
            transfer_request_parameter_record: Optional transfer request parameter record bytes
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.RequestTransferExit.make_request(
            transfer_request_parameter_record=transfer_request_parameter_record
        )
        response = self.send_request(request, timeout=timeout)
        return services.RequestTransferExit.interpret_response(response)
    
    def security_access(
        self,
        access_type: int,
        security_access_data: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> services.SecurityAccess.ServiceData:
        """
        Security access.
        
        Args:
            access_type: Access type (0x01=request seed, 0x02=send key)
            security_access_data: Optional security access data (e.g., key for send key)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.SecurityAccess.make_request(
            access_type=access_type,
            security_access_data=security_access_data
        )
        response = self.send_request(request, timeout=timeout)
        return services.SecurityAccess.interpret_response(response)
    
    def read_ecu_identification(
        self,
        ecu_identification_option: Optional[int] = None,
        timeout: float = 1.0
    ) -> services.ReadEcuIdentification.ServiceData:
        """
        Read ECU identification.
        
        Args:
            ecu_identification_option: Optional ECU identification option byte
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.ReadEcuIdentification.make_request(
            ecu_identification_option=ecu_identification_option
        )
        response = self.send_request(request, timeout=timeout)
        return services.ReadEcuIdentification.interpret_response(response)
    
    def dynamically_define_local_identifier(
        self,
        sub_function: int,
        definition_record: bytes,
        timeout: float = 1.0
    ) -> services.DynamicallyDefineLocalIdentifier.ServiceData:
        """
        Dynamically define local identifier.
        
        Args:
            sub_function: Sub-function (0x01=define by identifier, 0x02=define by memory address, 0x03=clear)
            definition_record: Definition record bytes
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with parsed response data
        """
        request = services.DynamicallyDefineLocalIdentifier.make_request(
            sub_function=sub_function,
            definition_record=definition_record
        )
        response = self.send_request(request, timeout=timeout)
        return services.DynamicallyDefineLocalIdentifier.interpret_response(response)
    
    def esc_code(
        self,
        esc_code_data: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> dict:
        """
        ESC code (KWP2000 specific, not part of standard diagnostic services).
        
        Args:
            esc_code_data: Optional ESC code data bytes
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with parsed response data
        """
        request = services.EscCode.make_request(esc_code_data=esc_code_data)
        response = self.send_request(request, timeout=timeout)
        return services.EscCode.interpret_response(response)

