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
SERVICE_READ_MEMORY_BY_ADDRESS = 0x23

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

# StartDiagnosticSession diagnostic modes
DIAGNOSTIC_MODE_OBD2 = 0x81  # Standardmodus OBD2-Modus (DT-SD-OBDIIMD)
DIAGNOSTIC_MODE_ECU_PROGRAMMING = 0x85  # Steuergeräte Programmiermodus (ECUPM)
DIAGNOSTIC_MODE_ECU_DEVELOPMENT = 0x86  # SG-Entwicklungs Modus (ECUDM)

# StartDiagnosticSession baudrate identifiers
BAUDRATE_9600 = 0x01  # 9.600 Baud seriell (PC9600)
BAUDRATE_19200 = 0x02  # 19.200 Baud seriell (PC19200)
BAUDRATE_38400 = 0x03  # 38.400 Baud seriell (PC38400)
BAUDRATE_57600 = 0x04  # 57.600 Baud seriell
BAUDRATE_115200 = 0x05  # 115.200 Baud seriell
BAUDRATE_125000 = 0x06  # seriell+Baudratenparameter 125.000 Baud
BAUDRATE_10400 = 0x14  # 10.400 Baud seriell
BAUDRATE_20800 = 0x34  # 20.800 Baud seriell

# Mapping from baudrate identifier to actual baudrate value
BAUDRATE_IDENTIFIER_TO_VALUE = {
    BAUDRATE_9600: 9600,
    BAUDRATE_19200: 19200,
    BAUDRATE_38400: 38400,
    BAUDRATE_57600: 57600,
    BAUDRATE_115200: 115200,
    BAUDRATE_125000: 125000,
    BAUDRATE_10400: 10400,
    BAUDRATE_20800: 20800,
}

def baudrate_identifier_to_value(identifier: int) -> int:
    """
    Convert baudrate identifier to actual baudrate value.
    
    Args:
        identifier: Baudrate identifier byte (e.g., 0x06 for 125000)
        
    Returns:
        Actual baudrate value in baud
        
    Raises:
        ValueError: If identifier is not recognized
    """
    if identifier not in BAUDRATE_IDENTIFIER_TO_VALUE:
        raise ValueError(f"Unknown baudrate identifier: 0x{identifier:02X}")
    return BAUDRATE_IDENTIFIER_TO_VALUE[identifier]

