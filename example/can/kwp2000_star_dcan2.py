"""Example: COM port KWP2000-STAR DCAN client.

This example demonstrates how to use the Kwp2000StarDcan adapter for KWP2000-STAR communication
with the high-level KWP2000Client interface. It performs diagnostic session setup, timing
parameter configuration, and memory read performance testing.
"""

import logging
import time

from kwp2000_can.protocols.can.kwp200_star_dcan.transport import Kwp2000StarDcan
from kwp2000_can.protocols.kwp2000 import (
    BAUDRATE_115200,
    TIMING_PARAMETER_MINIMAL
)
from kwp2000_can.protocols.kwp2000 import KWP2000Client


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
    # Configure COM port and adapter parameters
    COM_PORT = 'COM1'  # Change this to your COM port
    TARGET_ADDRESS = 0x12  # ECU address
    SOURCE_ADDRESS = 0xF1  # Tester address

    # Initialize KWP2000-STAR DCAN adapter
    adapter = Kwp2000StarDcan(
        port=COM_PORT,
        baudrate=115200,
        timeout=0.01,
        target=TARGET_ADDRESS,
        source=SOURCE_ADDRESS
    )

    # Create KWP2000 client using the STAR DCAN adapter
    client = KWP2000Client(adapter)

    try:
        # Open adapter connection
        adapter.open()
        print(f"Connected to {COM_PORT} at {adapter.baudrate} baud")
        print(f"Target address: 0x{adapter.target:02X}, Source address: 0x{adapter.source:02X}")

        with client:

            # Example: Read memory by address
            # Read 1 byte starting at memory address 0x5B90D8
            mem_addr = 0x5B90D8
            print(f"\nMeasuring memory request time at address 0x{mem_addr:08X}, size: 1 byte")
            print("Making 10 attempts...")

            times = []
            for attempt in range(1000):
                start_time = time.perf_counter()
                address_int = 0x77b0
                result = client.readMemoryByAddress2(
                    memory_address=address_int,
                    memory_size=1,
                    memory_type=5  # 5 = RAM (as per example code)
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
    finally:
        # Close adapter connection
        adapter.close()
        print("\nConnection closed.")

