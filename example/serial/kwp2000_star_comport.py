"""Example: COM port KWP2000-STAR client.

This example demonstrates how to use the COM port transport for KWP2000-STAR communication
with the high-level KWP2000Client interface. It requests maximum baudrate (125k) and changes
the comport baudrate accordingly.
"""

import logging
from kwp2000.client import KWP2000Client
from kwp2000_star.transport import KWP2000StarTransport
from kwp2000.constants import (
    BAUDRATE_115200,
    baudrate_identifier_to_value,
    TIMING_PARAMETER_MINIMAL
)

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
            
            # Identify the working baudrate
            print("\nIdentifying ECU baudrate...")
            working_baudrate = transport.identify_baudrate(client, verbose=True)
            
            if working_baudrate:
                print(f"✓ Found working baudrate: {working_baudrate} baud")
            else:
                print("✗ Could not identify baudrate, continuing with default 9600 baud")
                print("  (ECU may require initialization sequence or may not be responding)")
            
            # Set timing parameters to minimal values for fast communication
            print("\nSetting timing parameters to minimal values...")
            try:
                timing_response = client.access_timing_parameter(
                    p2min=TIMING_PARAMETER_MINIMAL['P2min'],
                    p2max=TIMING_PARAMETER_MINIMAL['P2max'],
                    p3min=TIMING_PARAMETER_MINIMAL['P3min'],
                    p3max=TIMING_PARAMETER_MINIMAL['P3max'],
                    p4min=TIMING_PARAMETER_MINIMAL['P4min']
                )
                print(f"Timing parameters set successfully:")
                print(f"  - Timing Parameter ID: 0x{timing_response.timing_parameter_id:02X}")
                if timing_response.timing_parameters:
                    tp = timing_response.timing_parameters
                    print(f"  - P2min: 0x{tp.p2min:02X}, P2max: 0x{tp.p2max:02X}")
                    print(f"  - P3min: 0x{tp.p3min:02X}, P3max: 0x{tp.p3max:02X}")
                    print(f"  - P4min: 0x{tp.p4min:02X}")
            except Exception as e:
                print(f"  - Warning: Could not set timing parameters: {e}")
            
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
