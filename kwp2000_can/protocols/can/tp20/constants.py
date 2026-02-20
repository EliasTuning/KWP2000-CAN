"""Constants for TP20 protocol."""

# Channel setup opcodes
OPCODE_SETUP_REQUEST = 0xC0
OPCODE_SETUP_POSITIVE_RESPONSE = 0xD0
OPCODE_SETUP_NEGATIVE_RESPONSE_MIN = 0xD6
OPCODE_SETUP_NEGATIVE_RESPONSE_MAX = 0xD8

# Channel parameter opcodes
OPCODE_PARAMETERS_REQUEST = 0xA0  # Sent by initiator to destination (6 byte)
OPCODE_PARAMETERS_RESPONSE = 0xA1  # Sent by destination to initiator (6 byte)
OPCODE_CHANNEL_TEST = 0xA3  # Keep channel alive (1 byte)
OPCODE_BREAK = 0xA4  # Receiver discards all data since last ACK (1 byte)
OPCODE_DISCONNECT = 0xA8  # Channel disconnect (1 byte)

# Broadcast opcodes
OPCODE_BROADCAST_REQUEST = 0x23
OPCODE_BROADCAST_RESPONSE = 0x24

# Data transmission opcodes (in upper nibble of first byte)
DATA_OP_WAIT_ACK_MORE = 0x0  # Waiting for ACK, more packets to follow
DATA_OP_WAIT_ACK_LAST = 0x1  # Waiting for ACK, this is last packet
DATA_OP_NO_ACK_MORE = 0x2  # Not waiting for ACK, more packets to follow
DATA_OP_NO_ACK_LAST = 0x3  # Not waiting for ACK, this is last packet
DATA_OP_ACK_READY = 0xB  # ACK, ready for next packet
DATA_OP_ACK_NOT_READY = 0x9  # ACK, not ready for next packet

# CAN ID constants
# Base for opening channel; actual request ID = CAN_ID_SETUP_REQUEST + dest (TP2.0_1_1 §4.1)
CAN_ID_SETUP_REQUEST = 0x200
CAN_ID_SETUP_RESPONSE_BASE = 0x200  # Response is 0x200 + destination logical address

# Static protocol parameters (TP2.0_1_1 §5.1)
T_WAIT_MS = 100  # Delay when receiver sends RNR (§6.3.2)
T_E_MS = 50  # Timeout for connection setup
TN_MS = 50  # Network latency; used for T_E + TN and T_CTpassiv
MNTC = 10  # Max repetitions for connection setup; channel closed when RC_E > MNTC (11 total attempts per §5.1 n+1)
MNT = 2  # Max retries for Ack request (T1 timeout); channel closed when RC_S > MNT
MNCT = 5  # Max CT timeouts before closing channel
T_CT_AKTIV_MS = 1000  # Connection test timer (active)
T_CT_PASSIV_MS = 1050  # T_CT_AKTIV_MS + TN_MS (passive)

# Default CAN IDs (negotiated during setup)
DEFAULT_RX_ID = 0x300  # Request destination module to transmit using this
DEFAULT_TX_ID = 0x740  # VW modules typically respond with this

# Application type
APP_TYPE_KWP = 0x01

# Timing parameter constants
TIMING_T2_DEFAULT = 0xFF
TIMING_T4_DEFAULT = 0xFF

# Default block size (number of packets before ACK)
DEFAULT_BLOCK_SIZE = 0x0F  # 15 packets
# Block size range per TP2.0_1_1 §5.2: 0 < BS < 16
BS_MIN = 1
BS_MAX = 15

# Max block retransmit requests (TP2.0_1_1 §5.1); channel closed after MNTB SN errors
MNTB = 5

# TPDU send priority per TP2.0_1_1 §4.2.2 Table 4 (lower number = higher priority)
PRIO_CA_CT = 1
PRIO_BR = 2
PRIO_ACK = 3
PRIO_DT_CS_DC = 4

# Sequence number mask (lower 4 bits)
SEQ_MASK = 0x0F
DATA_OP_MASK = 0xF0

# Response request values
RESP_REQ_RESPONSE_EXPECTED = 0x00
RESP_REQ_NO_RESPONSE = 0x55
RESP_REQ_NO_RESPONSE_ALT = 0xAA

