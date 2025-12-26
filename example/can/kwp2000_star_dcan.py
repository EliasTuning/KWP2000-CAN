"""Example: DCAN CAN KWP2000-STAR convenience wrapper.

This example demonstrates how to use the KWP2000-STAR protocol over CAN bus
using DCanCanConnection.
"""

# Import from the installed package (prefixed to avoid name clashes)
import time

# Example usage:
from kwp2000_can.protocols.can.kwp200_star_dcan.transport import Kwp2000StarDcan
from kwp2000_can.protocols.kwp2000 import KWP2000Client

if __name__ == "__main__":

    adapter = Kwp2000StarDcan(
        port="COM1",
        baudrate=115200,
        timeout=1.0,
        target=0x12,
        source=0xF1
    )
    adapter.open()

    star_client = KWP2000Client(adapter)
    with star_client:
        print("Connected via KWP2000-STAR over CAN bus (DCAN adapter)")

        while (True):
            # Read data by local identifier
            # data = star_client.read_ecu_identification(ecu_identification_option=0x80)
            data = star_client.read_data_by_common_identifier(0x2502)
            # data = star_client.tester_present()
            print(f"Data read: {data}")
            time.sleep(2)
