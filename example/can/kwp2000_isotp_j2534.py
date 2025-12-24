"""Example: J2534 ISO-TP KWP2000 convenience wrapper.

This example demonstrates how to use the ISO-TP convenience wrapper.
For production use, import directly from the package:

    from kwp2000.isotp import KWP2000_ISOTP_J2534
    # or use the alias:
    from kwp2000.isotp import KWP2000_UDS_J2534
"""

# Import from the package (works after pip install)
import time



# Example usage:
from kwp2000 import KWP2000Client
from kwp2000_star_can.transport import KWP2000StarTransportCAN

if __name__ == "__main__":

    from udsoncan.connections import J2534Connection

    conn = J2534Connection(windll='C:\Program Files (x86)\OpenECU\OpenPort 2.0\drivers\openport 2.0\op20pt32.dll',
                           rxid=0x612, txid=0x6F1)

    conn.open()

    transport = KWP2000StarTransportCAN(isotp_connection=conn)

    # Create KWP2000 client using the STAR CAN transport
    star_client = KWP2000Client(transport)

    with star_client:
        print("Connected via KWP2000-STAR over CAN bus")

        while(True):
            # Read data by local identifier
            data = star_client.read_ecu_identification(timeout=3)
            print(f"Data read: {data}")
            time.sleep(2)
