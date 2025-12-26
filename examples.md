# Examples

This library is built with a layered architecture similar to [udsoncan](https://udsoncan.readthedocs.io/en/latest/udsoncan/examples.html). You can work at different levels of abstraction depending on your needs.

## Table of Contents

- [Different Layers of Intelligence (1 to 4)](#different-layers-of-intelligence-1-to-4)
  - [1. Raw Connection](#1-raw-connection)
  - [2. Request and Responses](#2-request-and-responses)
  - [3. Services](#3-services)
  - [4. Client](#4-client)
- [Protocol-Specific Examples](#protocol-specific-examples)

---

## Different Layers of Intelligence (1 to 4)

In the following examples, we will start a routine with the RoutineControl service (0x31) in 4 different ways. We will start by crafting a binary payload manually, then add layers of interpretation making the code more comprehensive each time.

### 1. Raw Connection

At the lowest level, you work directly with raw bytes. This gives you full control but requires manual payload construction and response parsing.

```python
# Sends RoutineControl (0x31), ControlType=1 (start), RoutineID=0x1234
my_connection.send(b'\x31\x01\x12\x34')
payload = my_connection.wait_frame(timeout=1)

if payload == b'\x71\x01\x12\x34':
    print('Success!')
else:
    print('Start of routine 0x1234 failed')
```

### 2. Request and Responses

Using the `Request` and `Response` classes, you can build requests more cleanly and get structured responses.

```python
from kwp2000_can.protocols.kwp2000 import Request, Response, services

# Build request using service ID and data bytes
req = Request(services.RoutineControl.SERVICE_ID, b'\x01\x12\x34')
my_connection.send(req.get_data())

payload = my_connection.wait_frame(timeout=1)
response = Response.from_payload(payload)

if response.service == 0x31 and response.code == Response.Code.PositiveResponse:
    if response.data == b'\x01\x12\x34':
        print('Success!')
    else:
        print('Start of routine 0x1234 failed')
```

### 3. Services

Service classes provide `make_request()` and `interpret_response()` methods that handle the byte-level details for you.

```python
from kwp2000_can.protocols.kwp2000 import Request, Response, services

# Create request using service class
req = services.RoutineControl.make_request(
    control_type=services.RoutineControl.ControlType.startRoutine,
    routine_id=0x1234
)
my_connection.send(req.get_data())

payload = my_connection.wait_frame(timeout=1)
response = Response.from_payload(payload)

# Interpret response using service class
service_data = services.RoutineControl.interpret_response(response)

if (response.code == Response.Code.PositiveResponse
    and service_data.control_type_echo == 1
    and service_data.routine_id_echo == 0x1234):
    print('Success!')
else:
    print('Start of routine 0x1234 failed')
```

### 4. Client

The `KWP2000Client` provides the highest level of abstraction. It handles request building, sending, response parsing, and validation in a single method call.

```python
from kwp2000_can.protocols.kwp2000 import KWP2000Client

client = KWP2000Client(my_connection)

with client:
    try:
        # control_type_echo and routine_id_echo are validated by the client
        response = client.start_routine(routine_id=0x1234)
        print('Success!')
    except Exception:
        print('Start of routine 0x1234 failed')
```

---

## More Client Examples

### Starting a Diagnostic Session

```python
from kwp2000_can.protocols.kwp2000 import KWP2000Client

with KWP2000Client(transport) as client:
    # Start OBD2 diagnostic session
    response = client.startDiagnosticSession(diagnostic_mode=0x81)
    print(f"Session started: {response}")
    
    # With baudrate negotiation (for serial)
    response = client.startDiagnosticSession(
        diagnostic_mode=0x81,
        baudrate_identifier=0x05  # 115200 baud
    )
```

### Reading Memory

```python
with KWP2000Client(transport) as client:
    # Read memory by address
    result = client.readMemoryByAddress(
        memory_address=0x5B9000,
        memory_size=16
    )
    print(f"Data: {result.record_values.hex()}")
    print(f"Address echo: 0x{result.memory_address_echo:06X}")
    
    # Read memory with memory type (variant 2)
    result = client.readMemoryByAddress2(
        memory_address=0x5B9000,
        memory_type=0x00,  # ROM
        memory_size=16
    )
    print(f"Data: {result.record_values.hex()}")
```

### Reading ECU Identification

```python
with KWP2000Client(transport) as client:
    result = client.read_ecu_identification(ecu_identification_option=0x80)
    print(f"ECU ID: {result.ecu_identification_data.hex()}")
```

### Security Access

```python
from kwp2000_can.protocols.kwp2000 import services

with KWP2000Client(transport) as client:
    # Request seed
    seed_response = client.security_access(
        access_type=services.SecurityAccess.AccessType.REQUEST_SEED
    )
    seed = seed_response.security_access_data
    print(f"Seed: {seed.hex()}")
    
    # Calculate key (implement your algorithm)
    key = calculate_key(seed)
    
    # Send key
    key_response = client.security_access(
        access_type=services.SecurityAccess.AccessType.SEND_KEY,
        security_access_data=key
    )
    print("Security unlocked!")
```

### Keeping the Session Alive

```python
from kwp2000_can.protocols.kwp2000 import services

with KWP2000Client(transport) as client:
    # With response expected
    client.tester_present()
    
    # Without waiting for response (fire-and-forget)
    client.tester_present(
        response_required=services.TesterPresent.ResponseRequired.NO
    )
```

### Setting Timing Parameters

```python
from kwp2000_can.protocols.kwp2000 import TIMING_PARAMETER_MINIMAL

with KWP2000Client(transport) as client:
    # Set minimal timing for fast communication
    response = client.access_timing_parameter(
        timing_parameters=TIMING_PARAMETER_MINIMAL
    )
    print(f"Timing set: P2max = {response.timing_parameters.p2max}")
```

---

## Protocol-Specific Examples

For complete working examples with specific transports (J2534, K-DCAN, K-Line, etc.), see the `example/` directory:

| Protocol | File |
|----------|------|
| KWP2000 TP20 VAG via J2534 | `example/can/kwp2000_tp20_j2534.py` |
| KWP2000 CAN BMW via J2534 | `example/can/kwp2000_star_j2534.py` |
| KWP2000 CAN BMW via K-DCAN | `example/can/kwp2000_star_dcan.py` |
| KWP2000 BMW over K-Line | `example/serial/kwp2000_comport.py` |
| KWP2000-STAR over K-Line | `example/serial/kwp2000_star_comport.py` |
| DS2 BMW over K-Line | `example/serial/ds2_comport.py` |

---

## Additional Resources

- [services.md](services.md) — Complete list of implemented KWP2000 services
