"""Example: COM port DS2 client.

This example demonstrates how to use the COM port transport for DS2 communication.
For production use, import directly from the package:

    from ds2.client import DS2Client
    from ds2.comport_transport import ComportTransport
"""

import logging

from kwp2000_can.protocols.serial.ds2 import DS2Client, ComportTransport, MOTRONIC

try:
    import serial
except ImportError:
    raise ImportError("pyserial is required. Install it with: pip install pyserial")

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Example usage:
if __name__ == "__main__":
    # List available COM ports
    print("Available COM ports:")
    ports = ComportTransport.list_ports()
    if ports:
        for port in ports:
            print(f"  - {port}")
    else:
        print("  No COM ports found")
    
    # Configure your COM port here
    # On Windows: 'COM3', 'COM4', etc.
    # On Linux: '/dev/ttyUSB0', '/dev/ttyACM0', etc.
    COM_PORT = 'COM1'  # Change this to your COM port
    BAUD_RATE = 9600   # DS2 uses 9600 baud
    
    # Initialize transport and client
    transport = ComportTransport(
        port=COM_PORT,
        baudrate=BAUD_RATE,
        timeout=1.0,
        parity=serial.PARITY_EVEN  # DS2 uses even parity
    )
    
    client = DS2Client(transport)
    
    try:
        # Open connection
        with client:
            print(f"Connected to {COM_PORT} at {BAUD_RATE} baud")

            # Example: Read memory
            print("\nReading memory...")
            try:
                result = client.ident(address=MOTRONIC)
                print(f"Identification data: {result['data']}")

                # Read 16 bytes from EEPROM at address 0x000000
                memory_address = 0x005b9464
                result = client.read_memory_by_name(
                    address=MOTRONIC,
                    memory_type_name="rom",
                    memory_address=memory_address,
                    memory_size=2
                )
                print(f"Memory address echo: 0x{result.address_echo:08X}")
                print(f"Memory type echo: 0x{result.memory_type_echo:02X}")
                print(f"Size echo: {result.size_echo}")
                print(f"Memory data ({len(result.memory_data)} bytes): {result.memory_data.hex()}")
                print(f"Memory data (hex): {' '.join(f'{b:02X}' for b in result.memory_data)}")
            except Exception as e:
                print(f"Error reading memory: {e}")

            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
