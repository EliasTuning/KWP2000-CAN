# KWP2000-CAN

A Python library for automotive diagnostics implementing legacy protocol stacks commonly used on VAG and BMW platforms.

## Supported Protocols

| Protocol | Bus | Hardware | Use Case |
|----------|-----|----------|----------|
| **KWP2000 TP20** | CAN | J2534 adapter | VAG vehicles (~2004–2010, pre-UDS) |
| **KWP2000 CAN** | CAN | J2534 adapter | BMW vehicles (ISO-TP with address byte) |
| **KWP2000 CAN** | CAN | K-DCAN cable | BMW vehicles via USB adapter |
| **KWP2000** | K-Line | Serial/USB | BMW vehicles over K-Line |
| **DS2** | K-Line | Serial/USB | BMW vehicles (pre-KWP2000 era) |

## Installation

```bash
pip install kwp2000-can
```

For serial/K-Line communication, also install pyserial:

```bash
pip install pyserial
```

## Quick Start

```python
from kwp2000_can.protocols.kwp2000.can import KWP2000_TP20_J2534

with KWP2000_TP20_J2534() as client:
    data = client.readDataByLocalIdentifier(local_identifier=0x01)
    print(data)
```

See [examples.md](examples.md) for complete usage examples for all protocols.

## Features

- **Clean layering** — Compose transports and clients; context-manager friendly
- **KWP2000 services** — Sessions, Read/Write Memory, ECU Identification, Routine Control, Timing Parameters, and more
- **DS2 services** — Ident, Read/Write Memory, Activate/Deactivate tests
- **J2534 Pass-Thru** — Auto-detects DLL when possible
- **Serial transports** — pyserial-based with baudrate scanning

## BMW Protocol Notes

| Variant | Baudrate | Checksum |
|---------|----------|----------|
| KWP2000 | 10400 baud | Additive |
| KWP2000-STAR | 9600 baud | XOR |
| BMW-FAST | 115200 baud | Additive |

## Documentation

- [Examples](examples.md) — Complete usage examples for all protocols
- [Services](services.md) — KWP2000 service reference

## Testing

```bash
python -m pytest tests/
```

## Requirements

- Python 3.7+
- `python-can>=4.0.0`
- J2534-compatible hardware (for CAN protocols)
- pyserial (for K-Line protocols)

## License

MIT License — see [LICENSE](LICENSE) for details.
