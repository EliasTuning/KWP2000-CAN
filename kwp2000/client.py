"""Client class for KWP2000 communication."""

from typing import Optional
from kwp2000.transport import Transport
from kwp2000.request import Request
from kwp2000.response import Response
from kwp2000 import services
from kwp2000.exceptions import TimeoutException, NegativeResponseException


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
        timing_parameter_id: int,
        timing_values: Optional[bytes] = None,
        timeout: float = 1.0
    ) -> dict:
        """
        Access timing parameters.
        
        Args:
            timing_parameter_id: Timing parameter ID
            timing_values: Optional timing values to set
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data
        """
        request = services.AccessTimingParameter.make_request(
            timing_parameter_id=timing_parameter_id,
            timing_values=timing_values
        )
        response = self.send_request(request, timeout=timeout)
        return services.AccessTimingParameter.interpret_response(response)
    
    def startDiagnosticSession(
        self,
        session_type: int,
        timeout: float = 1.0
    ) -> dict:
        """
        Start diagnostic session.
        
        Args:
            session_type: Session type (e.g., 0x89 for extended diagnostic session)
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data containing:
                - session_type_echo: Echo of the requested session type
        """
        request = services.StartDiagnosticSession.make_request(
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

