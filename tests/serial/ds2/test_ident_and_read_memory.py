"""
Pytest tests for DS2 communication over serial port.
Tests ECU identification and memory reading functionality.
"""
import sys
from pathlib import Path

# Calculate paths
project_root = Path(__file__).parent.parent.parent.parent.resolve()
test_dir = Path(__file__).parent.parent.parent.resolve()  # tests/serial

# Remove any conflicting paths that might interfere with imports
conflicting_paths = [
    str(test_dir / 'ds2'),
    str(test_dir),
]
for path in conflicting_paths:
    normalized_path = str(Path(path).resolve())
    if normalized_path in sys.path:
        sys.path.remove(normalized_path)

# Ensure project root is at the beginning of sys.path (highest priority)
project_root_str = str(project_root)
if project_root_str in sys.path:
    sys.path.remove(project_root_str)
sys.path.insert(0, project_root_str)

# Clear any cached imports that might have been loaded from wrong location
modules_to_clear = ['ds2']
for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Import from project root packages
from kwp2000_can.protocols.serial.ds2.transport import MockTransport
from kwp2000_can.protocols.serial.ds2.client import DS2Client
from kwp2000_can.protocols.serial.ds2.frames import build_frame
from kwp2000_can.protocols.serial.ds2.constants import MOTRONIC, STATUS_OKAY, MEMORY_TYPE_ROM


def test_ident():
    """Test ECU identification via DS2."""
    # Create mock transport
    transport = MockTransport()
    
    # Create DS2 client
    client = DS2Client(transport)
    
    # Use context managers
    with client:
        print("Connected via DS2 serial")
        
        # Prepare request frame (will be built by client)
        # For ident: address=MOTRONIC (0x12), payload=[0x04, 0x00]
        request_frame = build_frame(MOTRONIC, bytes([0x04, 0x00]))
        
        # Queue echo frame (same as request)
        transport.queue_response(request_frame)
        
        # Queue response frame: STATUS_OKAY + identification data
        # Response payload: STATUS_OKAY (0xA0) + data bytes
        ident_data = bytes([0x12, 0x34, 0x56, 0x78])  # Example identification data
        response_payload = bytes([STATUS_OKAY]) + ident_data
        response_frame = build_frame(MOTRONIC, response_payload)
        transport.queue_response(response_frame)
        
        # Call ident service
        result = client.ident(address=MOTRONIC)
        
        # Assert data read successfully
        assert result is not None, "Ident response should not be None"
        assert 'data' in result, "Response should contain data"
        assert isinstance(result['data'], bytes), "Identification data should be bytes"
        assert len(result['data']) > 0, "Identification data should not be empty"
        assert result['data'] == ident_data, f"Expected ident data {ident_data.hex()}, got {result['data'].hex()}"
        
        print(f"ECU identification data: {result['data'].hex(' ').upper()}")
        print("Ident test completed successfully!")


def test_read_memory():
    """Test reading memory via DS2."""
    # Create mock transport
    transport = MockTransport()
    
    # Create DS2 client
    client = DS2Client(transport)
    
    # Use context managers
    with client:
        print("Connected via DS2 serial")
        
        # Prepare request: read 4 bytes from ROM at address 0x005B9464
        memory_address = 0x005B9464
        memory_size = 4
        memory_type = MEMORY_TYPE_ROM
        
        # Build request payload: CMD_READ_MEMORY (0x06) + memory_type + address (3 bytes) + size
        request_payload = bytes([
            0x06,  # CMD_READ_MEMORY
            memory_type,
            (memory_address >> 16) & 0xFF,  # Address high byte
            (memory_address >> 8) & 0xFF,   # Address middle byte
            memory_address & 0xFF,           # Address low byte
            memory_size
        ])
        request_frame = build_frame(MOTRONIC, request_payload)
        
        # Queue echo frame (same as request)
        transport.queue_response(request_frame)
        
        # Queue response frame: STATUS_OKAY + memory_type_echo + address_echo + size_echo + memory_data
        memory_data = bytes([0xAA, 0xBB, 0xCC, 0xDD])  # Example memory data
        response_payload = bytes([
            STATUS_OKAY,
            memory_type,  # memory_type_echo
            (memory_address >> 16) & 0xFF,  # address_echo high
            (memory_address >> 8) & 0xFF,   # address_echo middle
            memory_address & 0xFF,           # address_echo low
            memory_size  # size_echo
        ]) + memory_data
        response_frame = build_frame(MOTRONIC, response_payload)
        transport.queue_response(response_frame)
        
        # Call read_memory service
        result = client.read_memory(
            address=MOTRONIC,
            memory_type=memory_type,
            memory_address=memory_address,
            memory_size=memory_size
        )
        
        # Assert data read successfully
        assert result is not None, "Read memory response should not be None"
        assert hasattr(result, 'memory_data'), "Response should contain memory_data"
        assert isinstance(result.memory_data, bytes), "Memory data should be bytes"
        assert len(result.memory_data) == memory_size, f"Expected {memory_size} bytes, got {len(result.memory_data)}"
        assert result.memory_data == memory_data, f"Expected memory data {memory_data.hex()}, got {result.memory_data.hex()}"
        assert result.memory_type_echo == memory_type, f"Expected memory type echo {memory_type:02X}, got {result.memory_type_echo:02X}"
        assert result.address_echo == memory_address, f"Expected address echo 0x{memory_address:08X}, got 0x{result.address_echo:08X}"
        assert result.size_echo == memory_size, f"Expected size echo {memory_size}, got {result.size_echo}"
        
        print(f"Memory address echo: 0x{result.address_echo:08X}")
        print(f"Memory type echo: 0x{result.memory_type_echo:02X}")
        print(f"Size echo: {result.size_echo}")
        print(f"Memory data ({len(result.memory_data)} bytes): {result.memory_data.hex(' ').upper()}")
        print("Read memory test completed successfully!")

