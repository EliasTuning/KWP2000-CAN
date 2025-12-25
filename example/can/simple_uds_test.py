from udsoncan.client import Client
from udsoncan.connections import J2534Connection

conn = J2534Connection(windll='C:\Program Files (x86)\OpenECU\OpenPort 2.0\drivers\openport 2.0\op20pt32.dll',
                       rxid=0x612,
                       txid=0x6F1)  # Define the connection using the absolute path to the DLL, rxid and txid's for isotp

with Client(conn, request_timeout=1) as client:  # Application layer (UDS protocol)
    #client.change_session(1)
    client.tester_present()
    # ...
