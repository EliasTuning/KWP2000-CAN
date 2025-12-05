"""Constants for TP20 protocol."""

# Channel setup opcodes
OPCODE_SETUP_REQUEST = 0xC0
OPCODE_SETUP_POSITIVE_RESPONSE = 0xD0
OPCODE_SETUP_NEGATIVE_RESPONSE_MIN = 0xD6
OPCODE_SETUP_NEGATIVE_RESPONSE_MAX = 0xD8

# Channel parameter opcodes
OPCODE_PARAMETERS_REQUEST = 0xA0  # Destination module to initiator (6 byte)
OPCODE_PARAMETERS_RESPONSE = 0xA1  # Initiator to destination module (6 byte)
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
CAN_ID_SETUP_REQUEST = 0x200
CAN_ID_SETUP_RESPONSE_BASE = 0x200  # Response is 0x200 + destination logical address

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

# Sequence number mask (lower 4 bits)
SEQ_MASK = 0x0F
DATA_OP_MASK = 0xF0

# Response request values
RESP_REQ_RESPONSE_EXPECTED = 0x00
RESP_REQ_NO_RESPONSE = 0x55
RESP_REQ_NO_RESPONSE_ALT = 0xAA

