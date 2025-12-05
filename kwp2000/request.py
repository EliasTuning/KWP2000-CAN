"""Request class for KWP2000."""

from kwp2000.frames import build_frame


class Request:
    """
    Represents a KWP2000 request.
    
    Usage:
        req = Request(services.RoutineControl, b'\x01\x12\x34')
        payload = req.get_payload()
    """
    
    def __init__(
        self,
        service_id: int,
        data: bytes = b''
    ):
        """
        Create a request.
        
        Args:
            service_id: Service ID byte
            data: Data bytes (after service ID)
        """
        self.service_id = service_id
        self.data = bytes(data)
    
    def get_payload(self) -> bytes:
        """
        Get the complete frame payload (including header).
        
        Returns:
            Complete frame bytes ready to send
        """
        return build_frame(
            service_id=self.service_id,
            data=self.data
        )
    
    def get_data(self) -> bytes:
        """
        Get just the data bytes (service ID + data, no header).
        
        Returns:
            Data bytes
        """
        return bytes([self.service_id]) + bytes(self.data)
    def __str__(self):
        return self.get_data().hex()

