"""TP20 transport layer for sending and receiving byte data over CAN."""

import time
from typing import Optional
from tp20.can_connection import CanConnection
from tp20.constants import (
    CAN_ID_SETUP_REQUEST,
    CAN_ID_SETUP_RESPONSE_BASE,
    DEFAULT_RX_ID,
    DEFAULT_TX_ID,
    DATA_OP_WAIT_ACK_MORE,
    DATA_OP_WAIT_ACK_LAST,
    DATA_OP_NO_ACK_MORE,
    DATA_OP_NO_ACK_LAST,
    DATA_OP_ACK_READY,
    DATA_OP_ACK_NOT_READY,
    SEQ_MASK,
)
from tp20.frames import (
    build_setup_request,
    parse_setup_response,
    build_parameters_request,
    parse_parameters_response,
    build_data_frame,
    parse_data_frame,
    build_disconnect,
    build_channel_test,
)
from tp20.exceptions import (
    TP20Exception,
    TP20TimeoutException,
    TP20ChannelException,
    TP20DisconnectedException,
)


class TP20Transport:
    """
    TP20 transport layer that wraps a CAN connection.
    
    Handles TP20 protocol details like channel setup, segmentation, and reassembly.
    Sends and receives byte data directly.
    
    Usage:
        can_conn = MockCanConnection()
        transport = TP20Transport(can_conn, dest=0x01)
        with transport:
            transport.send(b'\\x10\\x89')
            data = transport.recv(timeout=1.0)
    """
    
    def __init__(
        self,
        can_connection: CanConnection,
        dest: int = 0x01,
        rx_id: int = DEFAULT_RX_ID,
        tx_id: int = DEFAULT_TX_ID,
        block_size: int = 0x0F,
        t1: int = 0x8A,
        t3: int = 0x32,
        timeout: float = 1.0
    ):
        """
        Initialize TP20 transport.
        
        Args:
            can_connection: CAN connection to use
            dest: Logical address of destination module (default: 0x01 for ECU)
            rx_id: Preferred RX CAN ID (default: 0x300)
            tx_id: Preferred TX CAN ID (default: 0x740)
            block_size: Block size for data transmission (default: 15)
            t1: Timing parameter 1 (default: 0x8A)
            t3: Timing parameter 3 (default: 0x32)
            timeout: Default timeout in seconds
        """
        self.can_connection = can_connection
        self.dest = dest
        self.preferred_rx_id = rx_id
        self.preferred_tx_id = tx_id
        self.block_size = block_size
        self.t1 = t1
        self.t3 = t3
        self.timeout = timeout
        
        # Channel state
        self._is_open = False
        self._channel_setup = False
        self._rx_can_id = None  # CAN ID we listen on
        self._tx_can_id = None  # CAN ID we transmit on
        self._remote_rx_id = None  # CAN ID remote listens on
        self._remote_tx_id = None  # CAN ID remote transmits on
        self._block_size = None
        self._t1 = None
        self._t3 = None
        
        # Receive buffer for reassembly
        self._receive_buffer = bytearray()
        self._receive_sequence = None
        self._receive_length = None
        
        # Send sequence number (continues across messages)
        self._send_sequence = 0
        
    def open(self) -> None:
        """Open the transport and establish TP20 channel."""
        if self._is_open:
            return
        
        self.can_connection.open()
        self._is_open = True
        
        try:
            self._setup_channel()
            self._negotiate_parameters()
        except Exception as e:
            self.close()
            raise TP20Exception(f"Failed to open TP20 channel: {e}") from e
    
    def close(self) -> None:
        """Close the transport and disconnect TP20 channel."""
        if not self._is_open:
            return
        
        if self._channel_setup:
            try:
                self._disconnect_channel()
            except Exception:
                pass  # Ignore errors during disconnect
        
        self.can_connection.close()
        self._is_open = False
        self._channel_setup = False
        self._receive_buffer.clear()
        self._receive_length = None
        self._receive_sequence = None
        self._send_sequence = 0  # Reset send sequence on close
    
    def send(self, data: bytes) -> None:
        """
        Send byte data over TP20.
        
        Args:
            data: Byte data to send
            
        Raises:
            TP20DisconnectedException: If channel is not set up
            TP20Exception: If send fails
        """
        if not self._is_open:
            raise TP20Exception("Transport not open")
        if not self._channel_setup:
            raise TP20DisconnectedException("Channel not set up")
        
        # Prepend length (2 bytes, big-endian)
        length = len(data)
        payload = bytearray()
        payload.append((length >> 8) & 0xFF)
        payload.append(length & 0xFF)
        payload.extend(data)
        
        # Segment and send
        self._send_segmented(payload)
    
    def recv(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Receive byte data over TP20.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Received byte data, or None if timeout occurs
            
        Raises:
            TP20TimeoutException: If timeout occurs
            TP20Exception: If receive fails
        """
        if not self._is_open:
            raise TP20Exception("Transport not open")
        if not self._channel_setup:
            raise TP20DisconnectedException("Channel not set up")
        
        start_time = time.time()
        self._receive_buffer.clear()
        self._receive_length = None
        self._receive_sequence = None
        
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TP20TimeoutException("Timeout waiting for frame")
            
            remaining_timeout = timeout - elapsed
            
            # Receive CAN frame
            frame = self.can_connection.recv_can_frame(timeout=remaining_timeout)
            if frame is None:
                continue
            
            can_id, data = frame
            
            # Only process frames on our RX CAN ID
            if can_id != self._rx_can_id:
                continue
            
            # Parse TP20 data frame
            try:
                opcode, sequence, payload = parse_data_frame(data)
            except ValueError:
                continue  # Skip invalid frames
            
            # Handle ACK frames
            if opcode == DATA_OP_ACK_READY or opcode == DATA_OP_ACK_NOT_READY:
                # We might need to handle these, but for now just continue
                continue
            
            # Handle data frames
            if opcode in (DATA_OP_WAIT_ACK_MORE, DATA_OP_WAIT_ACK_LAST,
                          DATA_OP_NO_ACK_MORE, DATA_OP_NO_ACK_LAST):
                # Check sequence number
                if self._receive_sequence is not None:
                    expected_seq = (self._receive_sequence + 1) & SEQ_MASK
                    if sequence != expected_seq:
                        # Sequence mismatch, reset
                        self._receive_buffer.clear()
                        self._receive_length = None
                        self._receive_sequence = None
                
                # First packet: extract length
                if self._receive_length is None:
                    if len(payload) < 2:
                        continue  # Need at least 2 bytes for length
                    self._receive_length = (payload[0] << 8) | payload[1]
                    # Add remaining payload after length bytes
                    self._receive_buffer.extend(payload[2:])
                    self._receive_sequence = sequence
                else:
                    # Subsequent packet: add all payload
                    self._receive_buffer.extend(payload)
                    self._receive_sequence = sequence
                
                # Send ACK if needed
                if opcode in (DATA_OP_WAIT_ACK_MORE, DATA_OP_WAIT_ACK_LAST):
                    # ACK uses the NEXT sequence number (sequence + 1)
                    ack_sequence = (sequence + 1) & SEQ_MASK
                    ack_frame = build_data_frame(DATA_OP_ACK_READY, ack_sequence, b'')
                    self.can_connection.send_can_frame(self._tx_can_id, ack_frame)
                
                # Check if complete
                if self._receive_length is not None:
                    # Buffer contains data after length bytes, so compare directly to data length
                    if len(self._receive_buffer) >= self._receive_length:
                        # Extract data (first _receive_length bytes from buffer)
                        received_data = bytes(self._receive_buffer[:self._receive_length])
                        # Reset for next frame
                        self._receive_buffer.clear()
                        self._receive_length = None
                        self._receive_sequence = None
                        return received_data
        
        return None
    
    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive a frame (KWP2000 Transport interface compatibility).
        
        This method wraps recv() but returns None on timeout instead of raising an exception,
        making TP20Transport compatible with KWP2000 Transport interface.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Received byte data, or None if timeout occurs
        """
        try:
            return self.recv(timeout=timeout)
        except TP20TimeoutException:
            return None
    
    def _setup_channel(self) -> None:
        """Setup TP20 channel."""
        # Build setup request
        # According to working example: request tx_id=0x0300 (where ECU should transmit)
        # rx_id is set to invalid (0x0000) so ECU will choose
        setup_req = build_setup_request(
            dest=self.dest,
            rx_id=0x0000,  # Invalid, ECU will choose
            tx_id=self.preferred_rx_id,  # Request ECU to transmit on this (0x300)
            rx_valid=True,   # rx_id is invalid
            tx_valid=False,  # tx_id is valid
        )
        
        # Send setup request
        self.can_connection.send_can_frame(CAN_ID_SETUP_REQUEST, setup_req)
        
        # Wait for response
        response_can_id = CAN_ID_SETUP_RESPONSE_BASE + self.dest
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            frame = self.can_connection.recv_can_frame(timeout=0.1)
            if frame is None:
                continue
            
            can_id, data = frame
            if can_id != response_can_id:
                continue
            
            try:
                dest, rx_id, tx_id, rx_valid, tx_valid, app_type = parse_setup_response(data)
                import logging
                logger = logging.getLogger()
                logger.debug(f"Setup response parsed: dest={dest:02X}, rx_id=0x{rx_id:03X}, tx_id=0x{tx_id:03X}, rx_valid={rx_valid}, tx_valid={tx_valid}, app_type={app_type:02X}")
                logger.debug(f"Setup response raw data: {data.hex()}")
                # From ECU's perspective: rx_id is where ECU listens, tx_id is where ECU transmits
                # So: we send TO ECU on rx_id, we listen FROM ECU on tx_id
                # But according to the working example, it's reversed:
                # We send on tx_id (0x740), we listen on rx_id (0x300)
                self._remote_rx_id = rx_id  # ECU listens here (we send TO ECU here, but example shows we send on tx_id)
                self._remote_tx_id = tx_id  # ECU transmits here (we listen FROM ECU here, but example shows we listen on rx_id)
                # Based on working example: we send on tx_id, listen on rx_id
                self._tx_can_id = tx_id     # We send on ECU's TX ID (0x740)
                self._rx_can_id = rx_id     # We listen on ECU's RX ID (0x300)
                self._channel_setup = True
                logger.info(f"TP20 channel setup: RX CAN ID=0x{self._rx_can_id:03X}, TX CAN ID=0x{self._tx_can_id:03X}")
                return
            except ValueError as e:
                if "Negative" in str(e):
                    raise TP20ChannelException(f"Channel setup failed: {e}") from e
                continue
        
        raise TP20TimeoutException("Timeout waiting for channel setup response")
    
    def _negotiate_parameters(self) -> None:
        """Negotiate channel parameters."""
        if not self._channel_setup:
            raise TP20ChannelException("Channel not set up")
        
        # Build parameters request
        params_req = build_parameters_request(
            block_size=self.block_size,
            t1=self.t1,
            t3=self.t3
        )
        
        # Send parameters request
        self.can_connection.send_can_frame(self._tx_can_id, params_req)
        
        # Wait for response
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            frame = self.can_connection.recv_can_frame(timeout=0.1)
            if frame is None:
                continue
            
            can_id, data = frame
            if can_id != self._rx_can_id:
                continue
            
            try:
                block_size, t1, t2, t3, t4 = parse_parameters_response(data)
                self._block_size = block_size
                self._t1 = t1
                self._t3 = t3
                return
            except ValueError:
                continue
        
        raise TP20TimeoutException("Timeout waiting for parameters response")
    
    def _send_segmented(self, payload: bytearray) -> None:
        """Send payload segmented into TP20 data frames."""
        if not self._channel_setup:
            raise TP20DisconnectedException("Channel not set up")
        
        sequence = self._send_sequence
        offset = 0
        payload_len = len(payload)
        block_count = 0
        
        while offset < payload_len:
            # Determine how much to send in this packet (max 7 bytes after opcode+seq)
            chunk_size = min(7, payload_len - offset)
            chunk = payload[offset:offset+chunk_size]
            
            # Determine if this is the last packet
            is_last = (offset + chunk_size >= payload_len)
            
            # Determine opcode based on whether we need ACK and if more packets follow
            # For simplicity, we'll request ACK every block_size packets or on last packet
            block_count += 1
            need_ack = (block_count >= self._block_size) or is_last
            
            if need_ack:
                if is_last:
                    opcode = DATA_OP_WAIT_ACK_LAST
                else:
                    opcode = DATA_OP_WAIT_ACK_MORE
            else:
                if is_last:
                    opcode = DATA_OP_NO_ACK_LAST
                else:
                    opcode = DATA_OP_NO_ACK_MORE
            
            # Build and send data frame
            data_frame = build_data_frame(opcode, sequence, chunk)
            self.can_connection.send_can_frame(self._tx_can_id, data_frame)
            
            # Wait for ACK if needed
            if need_ack:
                self._wait_for_ack(sequence)
            
            # Update for next packet
            offset += chunk_size
            sequence = (sequence + 1) & SEQ_MASK
            self._send_sequence = sequence  # Update global send sequence
            if need_ack:
                block_count = 0
            
            # Wait T3 between packets
            if offset < payload_len:
                time.sleep(self._t3 / 1000.0)  # T3 is in milliseconds
    
    def _wait_for_ack(self, sequence: int) -> None:
        """Wait for ACK for given sequence number."""
        start_time = time.time()
        frames_received = []
        
        while time.time() - start_time < self.timeout:
            frame = self.can_connection.recv_can_frame(timeout=0.1)
            if frame is None:
                continue
            
            can_id, data = frame
            frames_received.append((can_id, data.hex()))
            
            if can_id != self._rx_can_id:
                # Log unexpected CAN IDs for debugging
                import logging
                logger = logging.getLogger()
                logger.debug(f"Received frame on unexpected CAN ID: 0x{can_id:03X} (expected 0x{self._rx_can_id:03X}), data: {data.hex()}")
                continue
            
            try:
                opcode, seq, _ = parse_data_frame(data)
                # ACK sequence number is the NEXT sequence number (sequence + 1)
                # So if we sent sequence 0, we expect ACK with sequence 1
                expected_ack_seq = (sequence + 1) & SEQ_MASK
                if opcode in (DATA_OP_ACK_READY, DATA_OP_ACK_NOT_READY) and seq == expected_ack_seq:
                    if opcode == DATA_OP_ACK_NOT_READY:
                        # Wait a bit more
                        time.sleep(0.01)
                        continue
                    return
            except ValueError:
                continue
        
        # Log what we received before timeout
        import logging
        logger = logging.getLogger()
        logger.warning(f"Timeout waiting for ACK sequence {sequence}. Expected CAN ID: 0x{self._rx_can_id:03X}. Received frames: {frames_received}")
        raise TP20TimeoutException(f"Timeout waiting for ACK for sequence {sequence}")
    
    def _disconnect_channel(self) -> None:
        """Disconnect TP20 channel."""
        if not self._channel_setup:
            return
        
        disconnect_frame = build_disconnect()
        self.can_connection.send_can_frame(self._tx_can_id, disconnect_frame)
        
        # Wait for disconnect response (optional, but good practice)
        start_time = time.time()
        while time.time() - start_time < 0.5:  # Shorter timeout for disconnect
            frame = self.can_connection.recv_can_frame(timeout=0.1)
            if frame is None:
                continue
            
            can_id, data = frame
            if can_id == self._rx_can_id and len(data) == 1 and data[0] == 0xA8:
                break  # Got disconnect response
        
        self._channel_setup = False
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

