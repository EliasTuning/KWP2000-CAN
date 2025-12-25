"""Example: COM port KWP2000-STAR client.

This example demonstrates how to use the COM port transport for KWP2000-STAR communication
with the high-level KWP2000Client interface. It requests maximum baudrate (125k) and changes
the serial baudrate accordingly.
"""

import logging
import time

from kwp2000_star.transport import KWP2000StarTransport

from protocols.kwp2000 import (
    BAUDRATE_115200,
    baudrate_identifier_to_value,
    TIMING_PARAMETER_MINIMAL
)
from protocols.kwp2000 import KWP2000Client

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

            # Start diagnostic session with maximum baudrate (125k = 0x06)
            print("\nStarting diagnostic session with maximum baudrate (125k)...")
            response = client.startDiagnosticSession(
                diagnostic_mode=0x81,  # OBD2 mode
                baudrate_identifier=BAUDRATE_115200
            )
            transport.set_baudrate(baudrate_identifier_to_value(BAUDRATE_115200))

            # Set timing parameters to minimal values for fast communication
            print("\nSetting timing parameters to minimal values...")
            try:
                # Update transport's access_timings to use minimal values
                # This affects the wait_frame timeout calculation
                transport.set_access_timings(TIMING_PARAMETER_MINIMAL)
                print(f"Transport access timing parameters updated:")
                tp = TIMING_PARAMETER_MINIMAL
                print(f"  - P2min: 0x{tp.p2min:02X}, P2max: 0x{tp.p2max:02X}")
                print(f"  - P3min: 0x{tp.p3min:02X}, P3max: 0x{tp.p3max:02X}")
                print(f"  - P4min: 0x{tp.p4min:02X}")
                print(f"  - Calculated wait_frame timeout: {(tp.p2max * 25.0) / 1000.0:.3f} seconds")
                
                # Also set timing parameters on the ECU via service
                timing_response = client.access_timing_parameter(
                    timing_parameters=TIMING_PARAMETER_MINIMAL
                )
                print(f"ECU timing parameters set successfully:")
                print(f"  - Timing Parameter ID: 0x{timing_response.timing_parameter_id:02X}")
                if timing_response.timing_parameters:
                    tp = timing_response.timing_parameters
                    print(f"  - P2min: 0x{tp.p2min:02X}, P2max: 0x{tp.p2max:02X}")
                    print(f"  - P3min: 0x{tp.p3min:02X}, P3max: 0x{tp.p3max:02X}")
                    print(f"  - P4min: 0x{tp.p4min:02X}")
            except Exception as e:
                print(f"  - Warning: Could not set timing parameters: {e}")



            
            # Example: Read memory by address
            # Read 1 byte starting at memory address 0x5B90D8
            mem_addr = 0x5B90D8
            print(f"\nMeasuring memory request time at address 0x{mem_addr:08X}, size: 1 byte")
            print("Making 10 attempts...")
            
            times = []
            for attempt in range(10):
                start_time = time.perf_counter()
                result = client.readMemoryByAddress2(
                    memory_address=mem_addr,
                    memory_size=1,
                    memory_type=0
                )
                end_time = time.perf_counter()
                elapsed_time = (end_time - start_time) * 1000  # Convert to milliseconds
                times.append(elapsed_time)
                print(f"  Attempt {attempt + 1}: {elapsed_time:.2f} ms - Value: {result.record_values.hex()}")
            
            # Calculate statistics
            average_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"\nMemory Request Timing Results:")
            print(f"  Average time: {average_time:.2f} ms")
            print(f"  Minimum time: {min_time:.2f} ms")
            print(f"  Maximum time: {max_time:.2f} ms")
            print(f"  All times: {', '.join(f'{t:.2f}' for t in times)} ms")
            
            print("\nConnection established. Add your KWP2000 commands here.")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
