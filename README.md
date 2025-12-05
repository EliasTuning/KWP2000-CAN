# KWP2000-CAN

A Python library for KWP2000 (Keyword Protocol 2000) communication over CAN bus using TP20 transport protocol and J2534 interface. This library provides a clean, high-level API for automotive ECU diagnostics, similar in design to `udsoncan`.

## Features

- **KWP2000 Protocol Support**: Full implementation of KWP2000 diagnostic protocol
- **TP20 Transport Layer**: VW Transport Protocol 2.0 implementation for CAN bus communication
- **J2534 Interface**: Support for J2534 Pass-Thru devices (e.g., VAG-COM interfaces)
- **Clean API**: High-level client interface with context manager support
- **Service Layer**: Comprehensive implementation of KWP2000 services
  - Start/Stop Communication
  - Diagnostic Sessions
  - Routine Control
  - Data Reading/Writing
  - ECU Reset
  - Timing Parameter Access

## Installation

```bash
pip install kwp2000-can
```

## Quick Start

The easiest way to get started is using the convenience wrapper that handles the full communication chain:

```python
from kwp2000.can import KWP2000_TP20_J2534

# Initialize and connect to ECU
with KWP2000_TP20_J2534() as client:
    # Start extended diagnostic session
    response = client.startDiagnosticSession(session_type=0x89)
    print(f"Session started: {response}")
    
    # Read data by local identifier
    data = client.readDataByLocalIdentifier(local_identifier=0x01)
    print(f"Data read: {data}")
    
    # Start a routine
    routine_result = client.start_routine(routine_id=0x1234)
    print(f"Routine result: {routine_result}")
```

### Advanced Usage

For more control, you can build the communication chain manually:

```python
from j2534.can_connection import J2534CanConnection
from tp20.transport import TP20Transport
from kwp2000.client import KWP2000Client

# Create CAN connection
can_conn = J2534CanConnection(
    dll_path=None,  # Auto-detect J2534 DLL
    baudrate=500000
)

# Create TP20 transport
tp20 = TP20Transport(
    can_connection=can_conn,
    dest=0x01,      # ECU logical address
    rx_id=0x300,    # RX CAN ID
    tx_id=0x740     # TX CAN ID
)

# Create KWP2000 client
client = KWP2000Client(tp20)

# Use context managers
with tp20:
    with client:
        response = client.startDiagnosticSession(session_type=0x89)
        print(response)
```

## Protocol Support

### KWP2000 Services

| Service | ID | Status |
|---------|----|----|
| Start Communication | 0x81 | ✅ |
| Stop Communication | 0x82 | ✅ |
| Start Diagnostic Session | 0x10 | ✅ |
| Stop Diagnostic Session | 0x20 | ✅ |
| ECU Reset | 0x11 | ✅ |
| Read Data By Local Identifier | 0x21 | ✅ |
| Read Data By Identifier | 0x22 | ✅ |
| Write Data By Local Identifier | 0x3B | ✅ |
| Routine Control | 0x31 | ✅ |
| Request Routine Results | 0x33 | ✅ |
| Access Timing Parameter | 0x83 | ✅ |
| Send Data | 0x36 | ✅ |

### Transport Protocols

- **TP20**: VW Transport Protocol 2.0 over CAN ✅
- **J2534**: Pass-Thru interface support ✅

## Examples

See the `example/` directory for complete usage examples:

- `kwp2000_tp20_j2534.py`: Convenience wrapper example

## Testing

Run the test suite:

```bash
python -m pytest test/
```

## Requirements

- Python 3.7+
- `python-can>=4.0.0`
- J2534-compatible hardware interface (for hardware testing)

## Project Structure

```
KWP2000-CAN/
├── kwp2000/          # KWP2000 protocol implementation
│   ├── client.py     # High-level client API
│   ├── services.py   # Service implementations
│   ├── transport.py  # Transport interface
│   └── ...
├── tp20/             # TP20 transport protocol
│   ├── transport.py  # TP20 implementation
│   └── ...
├── j2534/            # J2534 interface
│   ├── can_connection.py
│   └── ...
└── example/          # Usage examples
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Links

- [PyPI Package](https://pypi.org/project/kwp2000-can/)
- [GitHub Repository](https://github.com/yourusername/KWP2000-CAN)

