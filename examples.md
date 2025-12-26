# Examples

Complete usage examples for all supported protocols.

## Table of Contents

- [KWP2000 TP20 VAG via J2534](#kwp2000-tp20-vag-via-j2534)
- [KWP2000 CAN BMW via J2534](#kwp2000-can-bmw-via-j2534)
- [KWP2000 CAN BMW via K-DCAN](#kwp2000-can-bmw-via-k-dcan)
- [KWP2000 BMW over K-Line](#kwp2000-bmw-over-k-line)
- [DS2 BMW over K-Line](#ds2-bmw-over-k-line)

---

## KWP2000 TP20 VAG via J2534

VAG TP20 protocol over CAN bus using a J2534 Pass-Thru adapter.

```python
from kwp2000_can.protocols.kwp2000.can import KWP2000_TP20_J2534

with KWP2000_TP20_J2534() as client:
    # Start diagnostic session
    response = client.startDiagnosticSession(session_type=0x89)
    print(f"Session started: {response}")
    
    # Read data by local identifier
    data = client.readDataByLocalIdentifier(local_identifier=0x01)
    print(f"Data: {data}")
```

---

## KWP2000 CAN BMW via J2534

BMW KWP2000-STAR protocol over CAN using a J2534 Pass-Thru adapter.

```python
from kwp2000_can.interface.j2534 import J2534CanConnection
from kwp2000_can.protocols.can import KWP2000StarTransportCAN
from kwp2000_can.protocols.kwp2000 import KWP2000Client

# Initialize J2534 connection (auto-detects DLL or specify path)
conn = J2534CanConnection(
    dll_path=r'C:\Program Files (x86)\OpenECU\OpenPort 2.0\drivers\openport 2.0\op20pt32.dll'
)
conn.open()

# Create transport with ECU addresses
transport = KWP2000StarTransportCAN(
    can_connection=conn,
    rx_id=0x612,
    tx_id=0x6F1
)

client = KWP2000Client(transport)

with client:
    # Read ECU identification
    data = client.read_ecu_identification(ecu_identification_option=0x80)
    print(f"ECU ID: {data}")
    
    # Read data by common identifier
    data = client.read_data_by_common_identifier(0x2502)
    print(f"Data: {data}")
```

---

## KWP2000 CAN BMW via K-DCAN

BMW KWP2000-STAR protocol using a K-DCAN USB adapter (serial over CAN).

```python
from kwp2000_can.protocols.can.kwp200_star_dcan.transport import Kwp2000StarDcan
from kwp2000_can.protocols.kwp2000 import KWP2000Client

# Initialize K-DCAN adapter
adapter = Kwp2000StarDcan(
    port="COM1",
    baudrate=115200,
    timeout=1.0,
    target=0x12,   # ECU address
    source=0xF1    # Tester address
)
adapter.open()

client = KWP2000Client(adapter)

with client:
    # Read data by common identifier
    data = client.read_data_by_common_identifier(0x2502)
    print(f"Data: {data}")
```

---

## KWP2000 BMW over K-Line

Standard KWP2000 protocol over K-Line serial connection.

```python
from kwp2000_can.interface.serial import ComportTransport
from kwp2000_can.protocols.kwp2000 import KWP2000Client

# Initialize serial transport
transport = ComportTransport(
    port="COM1",
    baudrate=125000,
    timeout=1.0
)

client = KWP2000Client(transport)

with client:
    # Start diagnostic session
    response = client.startDiagnosticSession(session_type=0x81)
    print(f"Session started: {response}")
    
    # Read memory by address
    result = client.readMemoryByAddress2(
        memory_address=0x005B9464,
        memory_size=16,
        memory_type=0
    )
    print(f"Memory data: {result.record_values.hex()}")
```

### KWP2000-STAR over K-Line

BMW KWP2000-STAR variant with XOR checksum and baudrate negotiation.

```python
from kwp2000_can.protocols.serial.kwp2000_star_serial.transport import KWP2000StarTransport
from kwp2000_can.protocols.kwp2000 import (
    KWP2000Client,
    BAUDRATE_115200,
    baudrate_identifier_to_value,
    TIMING_PARAMETER_MINIMAL
)

# Initialize transport (starts at 9600 baud)
transport = KWP2000StarTransport(
    port="COM1",
    baudrate=9600
)

client = KWP2000Client(transport)

with client:
    # Auto-detect working baudrate
    working_baudrate = transport.identify_baudrate(client, verbose=True)
    print(f"Found baudrate: {working_baudrate}")
    
    # Request higher baudrate from ECU
    response = client.startDiagnosticSession(
        diagnostic_mode=0x81,
        baudrate_identifier=BAUDRATE_115200
    )
    transport.set_baudrate(baudrate_identifier_to_value(BAUDRATE_115200))
    
    # Set minimal timing for fast communication
    transport.set_access_timings(TIMING_PARAMETER_MINIMAL)
    client.access_timing_parameter(timing_parameters=TIMING_PARAMETER_MINIMAL)
    
    # Read memory
    result = client.readMemoryByAddress2(
        memory_address=0x5B90D8,
        memory_size=1,
        memory_type=0
    )
    print(f"Value: {result.record_values.hex()}")
```

---

## DS2 BMW over K-Line

BMW DS2 protocol for older vehicles (pre-KWP2000 era).

```python
import serial
from kwp2000_can.protocols.serial.ds2 import DS2Client, ComportTransport, MOTRONIC

# List available COM ports
ports = ComportTransport.list_ports()
print(f"Available ports: {ports}")

# Initialize DS2 transport (9600 baud, even parity)
transport = ComportTransport(
    port="COM1",
    baudrate=9600,
    timeout=1.0,
    parity=serial.PARITY_EVEN
)

client = DS2Client(transport)

with client:
    # Read ECU identification
    ident = client.ident(address=MOTRONIC)
    print(f"Identification: {ident['data']}")
    
    # Read memory by name
    result = client.read_memory_by_name(
        address=MOTRONIC,
        memory_type_name="rom",
        memory_address=0x005B9464,
        memory_size=16
    )
    print(f"Address: 0x{result.address_echo:08X}")
    print(f"Memory type: 0x{result.memory_type_echo:02X}")
    print(f"Data: {result.memory_data.hex()}")
```

---

## Additional Resources

- See the `example/` directory for runnable scripts
- Check [services.md](services.md) for a complete list of KWP2000 services

