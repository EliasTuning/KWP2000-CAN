"""Request class for DS2."""


class Request:
    """
    Represents a DS2 request.
    
    Usage:
        req = Request(address=IKE, payload=b'\\x0c\\x0a\\x00\\x64')
        frame = req.get_frame()
    """
    
    def __init__(
        self,
        address: int,
        payload: bytes = b''
    ):
        """
        Create a request.
        
        Args:
            address: Target address byte
            payload: Payload bytes
        """
        self.address = address
        self.payload = bytes(payload)
    
    def get_frame(self) -> bytes:
        """
        Get the complete frame (including address, size, payload, checksum).
        
        Returns:
            Complete frame bytes ready to send
        """
        from .frames import build_frame
        return build_frame(self.address, self.payload)
    
    def get_payload(self) -> bytes:
        """
        Get just the payload bytes.
        
        Returns:
            Payload bytes
        """
        return bytes(self.payload)
    
    def __str__(self) -> str:
        return f"Request(address={self.address:02X}, payload={self.payload.hex()})"
