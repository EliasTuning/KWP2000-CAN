"""Example: J2534 CAN KWP2000-STAR convenience wrapper.

This example demonstrates how to use the KWP2000-STAR protocol over CAN bus
using J2534CanConnection.
"""

# Import from the package (works after pip install)
import time

# Example usage:
from kwp2000 import KWP2000Client
from kwp2000_star_can.transport import KWP2000StarTransportCAN

if __name__ == "__main__":

    from j2534.can_connection import J2534CanConnection

    conn = J2534CanConnection(dll_path=r'C:\Program Files (x86)\OpenECU\OpenPort 2.0\drivers\openport 2.0\op20pt32.dll')

    conn.open()

    transport = KWP2000StarTransportCAN(can_connection=conn, rx_id=0x612, tx_id=0x6F1)

    # Create KWP2000 client using the STAR CAN transport
    star_client = KWP2000Client(transport)

    with star_client:
        print("Connected via KWP2000-STAR over CAN bus")

        while(True):
            # Read data by local identifier
            data = star_client.read_ecu_identification(ecu_identification_option=0x80)
            print(f"Data read: {data}")
            time.sleep(2)
