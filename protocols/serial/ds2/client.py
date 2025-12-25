"""Client class for DS2 communication."""

from ds2 import services
from ds2.exceptions import TimeoutException
from ds2.request import Request
from ds2.transport import Transport

from protocols.serial.ds2.response import Response


class DS2Client:
    """
    High-level client for DS2 communication.
    
    Provides convenient methods for common operations.
    
    Usage:
        with DS2Client(transport) as client:
            result = client.read_memory(address=IKE, memory_type=0x03, memory_address=0x123456)
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
    
    def send_request(self, request: Request, timeout: float = 5.0) -> Response:
        """
        Send a request and wait for response.
        
        DS2 protocol flow:
        1. Send request frame
        2. Read echo (should match sent frame)
        3. Wait for reply
        
        Args:
            request: Request object to send
            timeout: Timeout in seconds
            
        Returns:
            Response object
            
        Raises:
            TimeoutException: If timeout occurs
        """
        if not self._is_open:
            raise RuntimeError("Client not open")
        
        # Send request
        frame = request.get_frame()
        self.transport.send(frame)
        
        # Read echo (as done in original implementation)
        echo = self.transport.wait_frame(timeout=timeout)
        if echo is None:
            raise TimeoutException("Timeout waiting for echo")
        
        # Wait for reply
        # Set timeout for reply (as done in original implementation)
        reply = self.transport.wait_frame(timeout=timeout)
        if reply is None:
            raise TimeoutException("Timeout waiting for response")
        
        # Parse response
        response = Response.from_frame(reply, expected_address=request.address)
        
        return response
    
    def ident(
        self,
        address: int,
        timeout: float = 5.0
    ) -> dict:
        """
        Request ECU identification.
        
        Args:
            address: Target ECU address (e.g., MOTRONIC)
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with response data containing identification information
        """
        request = services.Ident.make_request(address=address)
        response = self.send_request(request, timeout=timeout)
        return services.Ident.interpret_response(response)
    
    def read_memory(
        self,
        address: int,
        memory_type: int,
        memory_address: int,
        memory_size: int = 1,
        timeout: float = 5.0
    ) -> services.ReadMemory.ServiceData:
        """
        Read memory by address.
        
        Args:
            address: Target ECU address (e.g., IKE)
            memory_type: Memory type (0x01=ROM, 0x03=EEPROM, etc.)
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Number of bytes to read (default: 1)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information
            
        Raises:
            TimeoutException: If timeout occurs
            ValueError: If response is invalid
        """
        request = services.ReadMemory.make_request(
            address=address,
            memory_type=memory_type,
            memory_address=memory_address,
            memory_size=memory_size
        )
        response = self.send_request(request, timeout=timeout)
        return services.ReadMemory.interpret_response(response)
    
    def write_memory(
        self,
        address: int,
        memory_type: int,
        memory_address: int,
        memory_content: bytes,
        timeout: float = 5.0
    ) -> services.WriteMemory.ServiceData:
        """
        Write memory by address.
        
        Args:
            address: Target ECU address (e.g., IKE)
            memory_type: Memory type (0x01=ROM, 0x03=EEPROM, etc.)
            memory_address: Memory address (24-bit, 3 bytes)
            memory_content: Data bytes to write
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information
            
        Raises:
            TimeoutException: If timeout occurs
            ValueError: If response is invalid
        """
        request = services.WriteMemory.make_request(
            address=address,
            memory_type=memory_type,
            memory_address=memory_address,
            memory_content=memory_content
        )
        response = self.send_request(request, timeout=timeout)
        return services.WriteMemory.interpret_response(response)
    
    def read_memory_by_name(
        self,
        address: int,
        memory_type_name: str,
        memory_address: int,
        memory_size: int = 1,
        timeout: float = 5.0
    ) -> services.ReadMemory.ServiceData:
        """
        Read memory by address using memory type name.
        
        Args:
            address: Target ECU address (e.g., IKE)
            memory_type_name: Memory type name ('eeprom', 'rom', 'dpram', etc.)
            memory_address: Memory address (24-bit, 3 bytes)
            memory_size: Number of bytes to read (default: 1)
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information
        """
        memory_type = services.get_memory_type_by_name(memory_type_name)
        return self.read_memory(
            address=address,
            memory_type=memory_type,
            memory_address=memory_address,
            memory_size=memory_size,
            timeout=timeout
        )
    
    def write_memory_by_name(
        self,
        address: int,
        memory_type_name: str,
        memory_address: int,
        memory_content: bytes,
        timeout: float = 5.0
    ) -> services.WriteMemory.ServiceData:
        """
        Write memory by address using memory type name.
        
        Args:
            address: Target ECU address (e.g., IKE)
            memory_type_name: Memory type name ('eeprom', 'rom', 'dpram', etc.)
            memory_address: Memory address (24-bit, 3 bytes)
            memory_content: Data bytes to write
            timeout: Timeout in seconds
            
        Returns:
            ServiceData with response information
        """
        memory_type = services.get_memory_type_by_name(memory_type_name)
        return self.write_memory(
            address=address,
            memory_type=memory_type,
            memory_address=memory_address,
            memory_content=memory_content,
            timeout=timeout
        )
