# KWP2000 Services Implemented

This library implements the following KWP2000 services (see
`protocols/kwp2000/services.py`). IDs are hexadecimal.

## Communication / Session
| Service | ID | Notes |
|---------|----|-------|
| StartCommunication | 0x81 | Optional key bytes |
| StopCommunication | 0x82 |  |
| StartDiagnosticSession | 0x10 | Supports baudrate identifier |
| StopDiagnosticSession | 0x20 |  |
| TesterPresent | 0x3E | Positive response 0x7E |

## ECU Control
| Service | ID | Notes |
|---------|----|-------|
| ECUReset | 0x11 |  |
| AccessTimingParameter | 0x83 | Positive response 0xC3 |

## Data Transmission
| Service | ID | Notes |
|---------|----|-------|
| ReadDataByLocalIdentifier | 0x21 |  |
| ReadDataByCommonIdentifier | 0x22 | 2-byte identifier |
| ReadMemoryByAddress | 0x23 | 24-bit address; optional transmission mode |
| ReadMemoryByAddress2 | 0x23 | Variant with memory type |
| SetDataRates | 0x26 |  |
| WriteDataByCommonIdentifier | 0x2E |  |
| WriteDataByLocalIdentifier | 0x3B |  |
| WriteMemoryByAddress | 0x3D | 24-bit address |
| SendData | 0x84 |  |

## Diagnostic Trouble Codes
| Service | ID | Notes |
|---------|----|-------|
| ReadFreezeFrameData | 0x12 |  |
| ReadDiagnosticTroubleCodes | 0x13 | Optional count byte |
| ClearDiagnosticInformation | 0x14 |  |
| ReadStatusOfDiagnosticTroubleCodes | 0x17 |  |
| ReadDiagnosticTroubleCodesByStatus | 0x18 | Optional count byte |

## Input / Output Control
| Service | ID | Notes |
|---------|----|-------|
| InputOutputControlByCommonIdentifier | 0x2F |  |
| InputOutputControlByLocalIdentifier | 0x30 |  |

## Routine Control
| Service | ID | Notes |
|---------|----|-------|
| RoutineControl | 0x31 | Start/Stop/Request results (local ID) |
| StopRoutineByLocalIdentifier | 0x32 |  |
| RequestRoutineResultsByLocalIdentifier | 0x33 |  |
| StartRoutineByAddress | 0x38 | 24-bit address |
| StopRoutineByAddress | 0x39 | 24-bit address |
| RequestRoutineResultsByAddress | 0x3A | 24-bit address |

## Upload / Download
| Service | ID | Notes |
|---------|----|-------|
| RequestDownload | 0x34 | Optional compression/encryption |
| RequestUpload | 0x35 | Optional compression/encryption |
| TransferData | 0x36 | Block sequence number |
| RequestTransferExit | 0x37 |  |

## Security
| Service | ID | Notes |
|---------|----|-------|
| SecurityAccess | 0x27 | Seed/key (request seed, send key) |

## Identification / Configuration
| Service | ID | Notes |
|---------|----|-------|
| ReadEcuIdentification | 0x1A | Option byte optional |
| DynamicallyDefineLocalIdentifier | 0x2C | Define/clear |

## Other
| Service | ID | Notes |
|---------|----|-------|
| EscCode | 0x80 | Positive response 0xC0 |

