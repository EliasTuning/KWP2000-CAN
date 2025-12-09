"""Example: COM port KWP2000-STAR client.

This example demonstrates how to use the COM port transport for KWP2000-STAR communication
with the high-level KWP2000Client interface. It requests maximum baudrate (125k) and changes
the comport baudrate accordingly.
"""

import logging
from kwp2000.client import KWP2000Client
from kwp2000_star.transport import KWP2000StarTransport
from kwp2000.constants import BAUDRATE_115200, baudrate_identifier_to_value

try:
    import serial
except ImportError:
    raise ImportError("pyserial is required. Install it with: pip install pyserial")

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    # Configure COM port
    COM_PORT = 'COM1'  # Change this to your COM port
    
    # Initialize KWP2000-STAR transport (starts at default 9600 baud)
    transport = KWP2000StarTransport(
        port=COM_PORT,
        baudrate=9600  # Start with default baudrate
    )
    
    # Create KWP2000 client using the STAR transport
    client = KWP2000Client(transport)
    
    try:
        with client:
            print(f"Connected to {COM_PORT} at 9600 baud")
            
            # Start diagnostic session with maximum baudrate (125k = 0x06)
            print("\nStarting diagnostic session with maximum baudrate (125k)...")
            response = client.startDiagnosticSession(
                diagnostic_mode=0x81,  # OBD2 mode
                baudrate_identifier=BAUDRATE_115200
            )
            
            print(f"Diagnostic session started:")
            print(f"  - Diagnostic mode: 0x{response['diagnostic_mode']:02X}")
            if 'baudrate_identifier' in response:
                baudrate_id = response['baudrate_identifier']
                print(f"  - Baudrate identifier: 0x{baudrate_id:02X}")
                
                # Change the comport baudrate to match the negotiated baudrate
                try:
                    actual_baudrate = baudrate_identifier_to_value(baudrate_id)
                    print(f"  - Changing comport baudrate to {actual_baudrate}...")
                    transport.set_baudrate(actual_baudrate)
                    print(f"  - Comport baudrate changed successfully to {actual_baudrate}")
                except ValueError as e:
                    print(f"  - Warning: Could not change baudrate: {e}")
            
            # Example: Read memory by address
            # Read 4 bytes starting at memory address 0x005b9464
            mem_addr = 0x5B90D8
            print(f"\nReading memory at address 0x{mem_addr:08X}, size: 1 byte")
            result = client.readMemoryByAddress2(
                memory_address=mem_addr,
                memory_size=1,
                memory_type=0
            )
            print(f"Record values ({len(result.record_values)} bytes): {result.record_values.hex()}")
            print(f"Record values (hex): {' '.join(f'{b:02X}' for b in result.record_values)}")

            
            print("\nConnection established. Add your KWP2000 commands here.")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
