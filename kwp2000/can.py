"""J2534 TP20 KWP2000 convenience wrapper."""

from typing import Optional
from j2534.can_connection import J2534CanConnection
from tp20.transport import TP20Transport
from kwp2000.client import KWP2000Client


class KWP2000_TP20_J2534:
    """
    Convenience wrapper that initializes the full chain:
    J2534CanConnection -> TP20Transport -> KWP2000Client
    
    Usage:
        from kwp2000.can import KWP2000_TP20_J2534
        
        with KWP2000_TP20_J2534() as kwp2000_client:
            response = kwp2000_client.startDiagnosticSession(session_type=0x89)
    """
    
    def __init__(
        self,
        dll_path: Optional[str] = None,
        baudrate: int = 500000,
        dest: int = 0x01,
        rx_id: int = 0x300,
        tx_id: int = 0x740,
        block_size: int = 0x0F,
        t1: int = 0x8A,
        t3: int = 0x32,
        timeout: float = 1.0,
        debug: bool = False
    ):
        """
        Initialize the full chain.
        
        Args:
            dll_path: Path to J2534 DLL (optional, will auto-detect if None)
            baudrate: CAN bus baud rate (default: 500000)
            dest: Logical address of destination module (default: 0x01 for ECU)
            rx_id: Preferred RX CAN ID (default: 0x300)
            tx_id: Preferred TX CAN ID (default: 0x740)
            block_size: Block size for data transmission (default: 15)
            t1: Timing parameter 1 (default: 0x8A)
            t3: Timing parameter 3 (default: 0x32)
            timeout: Default timeout in seconds
            debug: Enable debug logging (default: False)
        """
        # Initialize J2534 CAN connection
        self._can_connection = J2534CanConnection(
            dll_path=dll_path,
            baudrate=baudrate,
            debug=debug
        )
        
        # Create TP20 transport layer
        self._tp20 = TP20Transport(
            can_connection=self._can_connection,
            dest=dest,
            rx_id=rx_id,
            tx_id=tx_id,
            block_size=block_size,
            t1=t1,
            t3=t3,
            timeout=timeout
        )
        
        # Create KWP2000 client
        self._kwp2000_client = KWP2000Client(self._tp20)
    
    def __enter__(self):
        """Context manager entry - opens all layers and yields the KWP2000 client."""
        # Open TP20 transport (which will open the CAN connection)
        self._tp20.__enter__()
        # Open KWP2000 client
        self._kwp2000_client.__enter__()
        return self._kwp2000_client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes all layers."""
        # Close KWP2000 client
        if self._kwp2000_client:
            self._kwp2000_client.__exit__(exc_type, exc_val, exc_tb)
        # Close TP20 transport (which will close the CAN connection)
        if self._tp20:
            self._tp20.__exit__(exc_type, exc_val, exc_tb)

