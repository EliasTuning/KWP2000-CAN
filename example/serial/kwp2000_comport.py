"""Example: COM port KWP2000 client.

This example demonstrates how to use the COM port transport for KWP2000 communication.
For production use, import directly from the package:

    from kwp2000.client import KWP2000Client
    from serial import ComportTransport
"""

import logging

from protocols.kwp2000 import KWP2000Client
from interface.serial import ComportTransport

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
    BAUD_RATE = 125000   # Default baud rate
    
    # Initialize transport and client
    transport = ComportTransport(
        port=COM_PORT,
        baudrate=BAUD_RATE,
        timeout=1.0
    )
    
    client = KWP2000Client(transport)
    mem_addr = 0x005b9464
    try:
        # Open connection
        with client:
            print(f"Connected to {COM_PORT} at {BAUD_RATE} baud")
            
            # Example: Start extended diagnostic session
            response = client.startDiagnosticSession(session_type=0x81)
            print(f"Session started: {response}")
            
            # Example: Read memory by address
            # Read 16 bytes starting at memory address 0x005b9464
            print(f"Reading memory at address 0x{mem_addr:08X}, size: 16 bytes")
            result = client.readMemoryByAddress2(
                memory_address=mem_addr,
                memory_size=4,
                memory_type=0
            )
            #print(f"Memory address echo: 0x{result.memory_address_echo:08X}")
            print(f"Record values ({len(result.record_values)} bytes): {result.record_values.hex()}")
            print(f"Record values (hex): {' '.join(f'{b:02X}' for b in result.record_values)}")
            
            # Example: Read memory with periodic transmission (slow mode)
            # Uncomment to test periodic reading:
            # print("\nStarting periodic memory read (slow mode)...")
            # while True:
            #     result = client.readMemoryByAddress(
            #         memory_address=mem_addr,
            #         memory_size=16,
            #         transmission_mode=services.ReadMemoryByAddress.TransmissionMode.slow,
            #         maximum_number_of_responses_to_send=10
            #     )
            #     print(f"Memory data: {result.record_values.hex()}")
            #     time.sleep(2)
            
            print("Connection established. Add your KWP2000 commands here.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
