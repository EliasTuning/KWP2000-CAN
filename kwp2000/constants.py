"""Constants for KWP2000 protocol."""

# Service IDs (Communication Services)
SERVICE_START_COMMUNICATION = 0x81
SERVICE_STOP_COMMUNICATION = 0x82
SERVICE_ACCESS_TIMING_PARAMETER = 0x83
SERVICE_SEND_DATA = 0x84

# Service IDs (Diagnostic Services - common ones)
SERVICE_START_DIAGNOSTIC_SESSION = 0x10
SERVICE_ROUTINE_CONTROL = 0x31
SERVICE_ECU_RESET = 0x11
SERVICE_READ_DATA_BY_LOCAL_IDENTIFIER = 0x21

# Response codes
RESPONSE_POSITIVE = 0x40  # Positive response offset
RESPONSE_NEGATIVE = 0x7F   # Negative response service ID

# Negative response codes
NRC_GENERAL_REJECT = 0x10
NRC_SERVICE_NOT_SUPPORTED = 0x11
NRC_SUB_FUNCTION_NOT_SUPPORTED = 0x12
NRC_INCORRECT_MESSAGE_LENGTH_OR_INVALID_FORMAT = 0x13
NRC_RESPONSE_PENDING = 0x78
NRC_CONDITIONS_NOT_CORRECT = 0x22
NRC_REQUEST_SEQUENCE_ERROR = 0x24

# Negative response codes mapping
NEGATIVE_RESPONSE_CODES = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported-invalidFormat",
    0x21: "busy-RepeatRequest",
    0x22: "conditionsNotCorrect or requestSequenceError",
    0x23: "routineNotComplete",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x35: "invalidKey",
    0x36: "exceedNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired",
    0x40: "downloadNotAccepted",
    0x41: "improperDownloadType",
    0x42: "cantDownloadToSpecifiedAddress",
    0x43: "cantDownloadNumberOfBytesRequested",
    0x50: "uploadNotAccepted",
    0x51: "improperUploadType",
    0x52: "cantUploadFromSpecifiedAddress",
    0x53: "cantUploadNumberOfBytesRequested",
    0x71: "transferSuspended",
    0x72: "transferAborted",
    0x74: "illegalAddressInBlockTransfer",
    0x75: "illegalByteCountInBlockTransfer",
    0x76: "illegalBlockTransferType",
    0x77: "blockTransferDataChecksumError",
    0x78: "reqCorrectlyRcvd-RspPending(requestCorrectlyReceived-ResponsePending)",
    0x79: "incorrectByteCountDuringBlockTransfer",
    0x80: "subFunctionNotSupportedInActiveDiagnosticSession",
    0x9A: "dataDecompressionFailed",
    0x9B: "dataDecryptionFailed",
    0xA0: "EcuNotResponding",
    0xA1: "EcuAddressUnknown"
}

# Format byte address modes
ADDRESS_MODE_NO_ADDRESS = 0x00
ADDRESS_MODE_EXCEPTION = 0x01  # CARB mode
ADDRESS_MODE_PHYSICAL = 0x02
ADDRESS_MODE_FUNCTIONAL = 0x03

# Format byte length mask
LENGTH_MASK = 0x3F  # Bits 0-5
ADDRESS_MODE_MASK = 0xC0  # Bits 6-7

# Default timing parameters (in milliseconds)
DEFAULT_P1 = 0
DEFAULT_P1_MAX = 20
DEFAULT_P2_MIN = 25
DEFAULT_P2_MAX = 50
DEFAULT_P3_MIN = 55
DEFAULT_P3_MAX = 5000
DEFAULT_P4_MIN = 5
DEFAULT_P4_MAX = 20

# Extended timing parameters (for physical addressing only)
EXTENDED_P2_MIN = 0
EXTENDED_P2_MAX = 1000
EXTENDED_P3_MIN = 0
EXTENDED_P3_MAX = 5000

# Timing parameter resolution (in milliseconds)
TIMING_RESOLUTION_P2 = 0.5
TIMING_RESOLUTION_P3 = 0.5
TIMING_RESOLUTION_P4 = 0.5

