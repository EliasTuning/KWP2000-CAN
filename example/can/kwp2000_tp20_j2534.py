"""Example: J2534 TP20 KWP2000 convenience wrapper.

This example demonstrates how to use the convenience wrapper.
For production use, import directly from the package:

    from kwp2000.can import KWP2000_TP20_J2534
"""

# Import from the package (works after pip install)
import time

from protocols.kwp2000 import KWP2000_TP20_J2534

# Example usage:
if __name__ == "__main__":
    # Initialize and connect to ECU
    with KWP2000_TP20_J2534() as client:
        # Start extended diagnostic session
        #response = client.startDiagnosticSession(session_type=0x89)
        #print(f"Session started: {response}")

        while(True):
            # Read data by local identifier
            data = client.readDataByLocalIdentifier(local_identifier=0x01)
            print(f"Data read: {data}")
            time.sleep(2)
