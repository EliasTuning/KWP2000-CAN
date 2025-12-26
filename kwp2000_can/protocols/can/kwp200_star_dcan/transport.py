"""
KWP2000-STAR DCAN adapter stub.

This module provides a stub implementation of the Kwp2000StarDcan class
for serial-based CAN communication.
"""
import logging
from typing import Optional

import serial
from kwp2000_can.protocols.kwp2000 import Transport
from kwp2000_can.interface.serial.comport_transport import ComportTransport


class Kwp2000StarDcan(Transport):
    """
    Stub class for KWP2000-STAR DCAN adapter.
    
    This adapter communicates with a CAN interface over a serial port
    (e.g., USB-to-CAN adapter) using the KWP2000-STAR protocol.
    
    Args:
        port: Serial port name (e.g., 'COM1' on Windows, '/dev/ttyUSB0' on Linux)
        baudrate: Baud rate for serial communication (default: 115200)
        timeout: Timeout in seconds for operations (default: 1.0)
        target: Target address (ECU address) for CAN communication
        source: Source address (tester address) for CAN communication
    """

    def __init__(
            self,
            port: str,
            baudrate: int = 115200,
            timeout: float = 1.0,
            target: int = 0x12,
            source: int = 0xF1,
            bytesize: int = serial.EIGHTBITS,
            parity: str = serial.PARITY_NONE,
            stopbits: float = serial.STOPBITS_TWO
    ):
        """
        Initialize the KWP2000-STAR DCAN adapter.
        
        Args:
            port: Serial port name
            baudrate: Baud rate for serial communication
            timeout: Timeout in seconds
            target: Target address (ECU address)
            source: Source address (tester address)
            bytesize: Number of data bits (default: 8)
            parity: Parity setting (default: NONE)
            stopbits: Number of stop bits (default: 2)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.target = target
        self.source = source
        self._is_open = False
        self.logger = logging.getLogger(__name__)

        self._comport_transport = ComportTransport(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            logger=self.logger
        )

    def open(self) -> None:
        """
        Open the serial port connection.
        
        Raises:
            NotImplementedError: This is a stub implementation
        """
        if self._is_open:
            return
        # Stub implementation
        self._is_open = True
        self._comport_transport.open()

    def close(self) -> None:
        """
        Close the serial port connection.
        
        Raises:
            NotImplementedError: This is a stub implementation
        """
        if not self._is_open:
            return
        # Stub implementation
        self._is_open = False

    def _build_send_frame_short(self, data: bytes) -> bytearray:
        """
        Build a short format send frame (for payload length <= 0x3F).
        
        Frame structure: [0x80 | length, ECU address, Tester address, payload..., checksum]
        
        Args:
            data: Payload data to send (bytes)
            
        Returns:
            Complete frame as bytearray (without checksum, checksum will be added separately)
        """
        send_data_length = len(data)
        telegram = bytearray([0x80 | send_data_length, self.target, self.source])
        telegram.extend(data)
        return telegram
    
    def _build_send_frame_long(self, data: bytes) -> bytearray:
        """
        Build a long format send frame (for payload length > 0x3F).
        
        Frame structure: [0x80, ECU address, Tester address, length, payload..., checksum]
        
        Args:
            data: Payload data to send (bytes)
            
        Returns:
            Complete frame as bytearray (without checksum, checksum will be added separately)
        """
        send_data_length = len(data)
        telegram = bytearray([0x80, self.target, self.source, send_data_length])
        telegram.extend(data)
        return telegram

    def send(self, data: bytes) -> None:
        """
        Send a KWP2000 telegram with checksum.
        
        Uses short format for payload length <= 0x3F, long format otherwise.
        Short format: [0x80 | length, target (ECU), source (tester), payload..., checksum]
        Long format: [0x80, target (ECU), source (tester), length, payload..., checksum]

        Args:
            data: Payload data to send (bytes)
            
        Raises:
            ValueError: If payload is too large or connection is not open
            RuntimeError: If connection is not open
        """
        if not self._is_open:
            raise RuntimeError("Connection is not open. Call open() first.")
        
        if not isinstance(data, bytes):
            raise TypeError(f"Expected bytes, got {type(data).__name__}")
        
        send_data_length = len(data)
        
        # Build telegram using appropriate format
        if send_data_length > 0x3F:
            telegram = self._build_send_frame_long(data)
        else:
            telegram = self._build_send_frame_short(data)
        
        # Calculate checksum (covers entire frame except checksum byte)
        checksum = self._calculate_checksum(telegram)
        telegram.append(checksum)
        
        try:
            self._comport_transport.send(telegram)
        except Exception as e:
            raise RuntimeError(f"Failed to send telegram: {e}") from e

    def _parse_receive_frame_short(self, data: bytes) -> bytes:
        """
        Parse a short format receive frame (for payload length <= 0x3F).
        
        Frame structure: [0x80 | length, source (tester), target (ECU), payload..., checksum]
        
        Args:
            data: Complete frame bytes including header and checksum
            
        Returns:
            Payload bytes (without header and checksum)
            
        Raises:
            ValueError: If frame structure is invalid, addresses don't match, or checksum is incorrect
        """
        # Validate minimum frame length (length byte + source + target + checksum = 4 bytes minimum)
        if len(data) < 4:
            raise ValueError(f"Frame too short: received {len(data)} bytes, minimum 4 bytes required")
        
        # Extract and validate length byte
        length_byte = data[0]
        if (length_byte & 0x80) == 0:
            raise ValueError(f"Invalid length byte: 0x{length_byte:02X} (must have 0x80 bit set)")
        
        expected_payload_len = length_byte & 0x7F
        expected_frame_len = 4 + expected_payload_len  # length + source + target + payload + checksum
        
        if len(data) != expected_frame_len:
            raise ValueError(
                f"Frame length mismatch: expected {expected_frame_len} bytes "
                f"(payload: {expected_payload_len}), but received {len(data)} bytes"
            )
        
        # Validate addresses (incoming frame: [length, source(tester), target(ECU), ...])
        # data[1] is the source (tester address) - should match self.source
        if data[1] != self.source:
            raise ValueError(
                f"Source address mismatch: expected tester address 0x{self.source:02X}, "
                f"but received 0x{data[1]:02X}"
            )
        
        # data[2] is the target (ECU address) - should match self.target
        if data[2] != self.target:
            raise ValueError(
                f"Target address mismatch: expected ECU address 0x{self.target:02X}, "
                f"but received 0x{data[2]:02X}"
            )
        
        # Extract payload (excluding header and checksum)
        payload = data[3:-1]
        received_checksum = data[-1]
        
        # Calculate and validate checksum (checksum covers entire frame except checksum byte)
        calculated_checksum = self._calculate_checksum(data[:-1])
        if received_checksum != calculated_checksum:
            raise ValueError(
                f"Checksum mismatch: calculated 0x{calculated_checksum:02X}, "
                f"received 0x{received_checksum:02X}"
            )
        
        return payload
    
    def _parse_receive_frame_long(self, data: bytes) -> bytes:
        """
        Parse a long format receive frame (for payload length > 0x3F).
        
        Frame structure: [0x80, source (tester), target (ECU), length, payload..., checksum]
        
        Args:
            data: Complete frame bytes including header and checksum
            
        Returns:
            Payload bytes (without header and checksum)
            
        Raises:
            ValueError: If frame structure is invalid, addresses don't match, or checksum is incorrect
        """
        # Validate minimum frame length (0x80 + source + target + length + checksum = 5 bytes minimum)
        if len(data) < 5:
            raise ValueError(f"Frame too short: received {len(data)} bytes, minimum 5 bytes required")
        
        # Validate first byte is 0x80
        if data[0] != 0x80:
            raise ValueError(f"Invalid first byte: expected 0x80, but received 0x{data[0]:02X}")
        
        # Validate addresses (incoming frame: [0x80, source(tester), target(ECU), length, ...])
        # data[1] is the source (tester address) - should match self.source
        if data[1] != self.source:
            raise ValueError(
                f"Source address mismatch: expected tester address 0x{self.source:02X}, "
                f"but received 0x{data[1]:02X}"
            )
        
        # data[2] is the target (ECU address) - should match self.target
        if data[2] != self.target:
            raise ValueError(
                f"Target address mismatch: expected ECU address 0x{self.target:02X}, "
                f"but received 0x{data[2]:02X}"
            )
        
        # Extract payload length from byte 3
        expected_payload_len = data[3]
        expected_frame_len = 5 + expected_payload_len  # 0x80 + source + target + length + payload + checksum
        
        if len(data) != expected_frame_len:
            raise ValueError(
                f"Frame length mismatch: expected {expected_frame_len} bytes "
                f"(payload: {expected_payload_len}), but received {len(data)} bytes"
            )
        
        # Extract payload (excluding header and checksum)
        payload = data[4:-1]
        received_checksum = data[-1]
        
        # Calculate and validate checksum (checksum covers entire frame except checksum byte)
        calculated_checksum = self._calculate_checksum(data[:-1])
        if received_checksum != calculated_checksum:
            raise ValueError(
                f"Checksum mismatch: calculated 0x{calculated_checksum:02X}, "
                f"received 0x{received_checksum:02X}"
            )
        
        return payload

    def wait_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Wait for and receive a KWP2000 telegram frame.
        
        Automatically detects frame format:
        - Short format: [0x80 | length, source (tester), target (ECU), payload..., checksum]
        - Long format: [0x80, source (tester), target (ECU), length, payload..., checksum]
        
        Args:
            timeout: Timeout in seconds for receiving the frame
            
        Returns:
            Payload bytes (without header and checksum), or None if timeout
            
        Raises:
            ValueError: If frame structure is invalid, addresses don't match, or checksum is incorrect
            TimeoutError: If no frame is received within timeout
        """
        data = self._comport_transport.wait_frame(timeout)
        
        # Handle timeout (None return)
        if data is None:
            raise TimeoutError(f"No frame received within {timeout} seconds")
        
        # Validate minimum frame length
        if len(data) < 4:
            raise ValueError(f"Frame too short: received {len(data)} bytes, minimum 4 bytes required")
        
        # Detect frame format based on first byte
        if data[0] == 0x80:
            # Long format: [0x80, source, target, length, payload..., checksum]
            return self._parse_receive_frame_long(data)
        else:
            # Short format: [0x80 | length, source, target, payload..., checksum]
            return self._parse_receive_frame_short(data)

    def _calculate_checksum(self, data: bytes) -> int:
        """
        Calculate 8-bit checksum (sum of all bytes, modulo 256).
        
        Args:
            data: Bytes to calculate checksum for
            
        Returns:
            Checksum value (0-255)
        """
        return sum(data) & 0xFF

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
