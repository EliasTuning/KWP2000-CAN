"""Example: DCAN CAN KWP2000-STAR convenience wrapper.

This example demonstrates how to use the KWP2000-STAR protocol over CAN bus
using DCanCanConnection.
"""

# Import from the installed package (prefixed to avoid name clashes)
import time

from kwp2000_can.interface.dcan import DCanCanConnection
from kwp2000_can.protocols.can import KWP2000StarTransportCAN
# Example usage:
from kwp2000_can.protocols.kwp2000 import KWP2000Client

if __name__ == "__main__":

    # Create DCAN connection
    # Adjust port, baudrate, rx_id, and tx_id according to your setup
    conn = DCanCanConnection(
        port='COM1',  # Change to your serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
        baudrate=115200,
        rx_id=0x612,  # CAN ID to receive frames on
        tx_id=0x6F1   # CAN ID to send frames on
    )

    conn.open()

    transport = KWP2000StarTransportCAN(can_connection=conn, rx_id=0x612, tx_id=0x6F1)

    # Create KWP2000 client using the STAR CAN transport
    star_client = KWP2000Client(transport)

    with star_client:
        print("Connected via KWP2000-STAR over CAN bus (DCAN adapter)")

        while(True):
            # Read data by local identifier
            #data = star_client.read_ecu_identification(ecu_identification_option=0x80)
            data = star_client.read_data_by_common_identifier(0x2502)
            #data = star_client.tester_present()
            print(f"Data read: {data}")
            time.sleep(2)

