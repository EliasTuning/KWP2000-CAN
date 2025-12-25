# KWP2000-CAN

A Python library for automotive diagnostics. It implements multiple legacy
protocol stacks that are still common on VAG/BMW platforms:

- KWP2000 over TP20 on CAN with J2534
- BMW-style KWP2000-STAR over CAN (ISO-TP with address byte)
- KWP2000-STAR over serial 
- BMW DS2 over serial

Everything is exposed through small transport classes and high-level clients so
you can assemble only the layers you need.

## Features

- **Multiple stacks**
  - KWP2000 over TP20 on CAN (VAG) via J2534
  - KWP2000-STAR over CAN (BMW ISO-TP + address byte)
  - KWP2000-STAR over serial
  - DS2 over serial (BMW pre-KWP/UDS)
- **Clean layering**: compose transports + clients; context-manager friendly
- **Service layers**
  - KWP2000 services: Start/Stop Comm, Sessions, Routine Control, Read/Write Data,
    ECU Reset, Timing Parameter Access, Send Data, etc.
  - DS2 services: ident, read/write memory, activate/deactivate tests, etc.
- **Interfaces**
  - J2534 Pass-Thru (auto-detects DLL when possible)
  - CAN abstraction + mock connection for tests
  - Serial transports with pyserial
- **Timing helpers**: shared timing parameter objects across transports
- **Examples & tests**: reference scripts under `example/` and pytest cases under `tests/`

## Installation

```bash
pip install kwp2000-can
```

For serial stacks install pyserial if you do not have it already:

```bash
pip install pyserial
```

## Protocol Support

### Stacks at a Glance

| Stack | Transport | Hardware | Module / Entry point | Notes |
|-------|-----------|----------|----------------------|-------|
| KWP2000 over TP20 | CAN  | J2534 | `protocols.kwp2000.can.KWP2000_TP20_J2534` | VAG TP20 framing (used ~2004–2010, pre-UDS); auto DLL detection |
| KWP2000-STAR (BMW) | CAN | J2534 | Uses address byte + ISO-TP PCI; flow control handled for you |
| KWP2000-STAR (BMW) | Serial | pyserial COM port | `protocols.serial.kwp2000_star_serial.transport.KWP2000StarTransport` | Includes baudrate scan helper and checksum handling |
| DS2 (BMW) | Serial | pyserial COM port | `protocols.serial.ds2` (`ComportTransport`, `DS2Client`) | Classic BMW DS2 framing with echo + reply handling |

### BMW protocol specifics

- KWP2000 (BMW) typically runs at **10400 baud** with an additive checksum.
- KWP2000\* / STAR uses **9600 baud** with an **XOR checksum**.
- BMW-FAST is essentially KWP2000 at **115200 baud** (same framing, higher speed).

### KWP2000 Services (implemented)

See the full list with notes in [services.md](services.md).


## Examples

See the `example/` directory for complete usage examples:

- `kwp2000_tp20_j2534.py`: VAG TP20
- `kwp2000_star_j2534.py`: KWP2000-STAR over CAN (J2534)
- `kwp2000_star_comport.py`: KWP2000-STAR over serial
- `ds2_comport.py`: DS2 over serial

### KWP2000-STAR over CAN (BMW)

```python
from interface.j2534 import J2534CanConnection
from protocols.can.kwp2000_star_can import KWP2000StarTransportCAN
from protocols.kwp2000 import KWP2000Client

conn = J2534CanConnection(baudrate=500000)
transport = KWP2000StarTransportCAN(conn, rx_id=0x612, tx_id=0x6F1)
client = KWP2000Client(transport)

with transport, client:
    resp = client.startDiagnosticSession(session_type=0x81)
    print(resp)
```

### KWP2000-STAR over Serial

```python
from protocols.serial.kwp2000_star_serial.transport import KWP2000StarTransport
from protocols.kwp2000 import KWP2000Client

transport = KWP2000StarTransport(port="COM3", baudrate=9600)
client = KWP2000Client(transport)

with transport, client:
    resp = client.tester_present(timeout=0.2)
    print(resp)
```

### DS2 over Serial

```python
from protocols.serial.ds2 import ComportTransport, DS2Client, services

transport = ComportTransport(port="COM3", baudrate=9600)

with DS2Client(transport) as client:
    ident = client.ident(address=services.MOTRONIC)
    print(ident)
```

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

## Requirements

- Python 3.7+
- `python-can>=4.0.0`
- J2534-compatible hardware interface (for hardware testing)

## Project Structure

```
KWP2000-CAN/
├── protocols/
│   ├── kwp2000/                     # KWP2000 core (services, client, timing)
│   ├── can/tp20/                    # TP20 transport + timing
│   ├── can/kwp2000_star_can/        # BMW KWP2000-STAR over CAN
│   ├── serial/kwp2000_star_serial/  # BMW KWP2000-STAR over serial
│   └── serial/ds2/                  # BMW DS2 over serial
├── interface/
│   ├── j2534/                       # J2534 bindings + auto DLL detection
│   └── serial/                      # Shared COM transport helpers
├── example/                         # Usage examples per stack
└── tests/                           # Pytest coverage (CAN + TP20 flows)
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Links

- [PyPI Package](https://pypi.org/project/kwp2000-can/)
- [GitHub Repository](https://github.com/yourusername/KWP2000-CAN)

