"""Exception classes for TP20 library."""


class TP20Exception(Exception):
    """Base exception for all TP20 errors."""
    pass


class TP20TimeoutException(TP20Exception):
    """Raised when a timeout occurs waiting for a TP20 response."""
    pass


class TP20ChannelException(TP20Exception):
    """Raised when channel setup or negotiation fails."""
    pass


class TP20InvalidFrameException(TP20Exception):
    """Raised when a TP20 frame cannot be parsed."""
    pass


class TP20NegativeResponseException(TP20Exception):
    """Raised when a negative response is received during channel setup."""
    def __init__(self, opcode, message=None):
        self.opcode = opcode
        self.message = message
        super().__init__(f"TP20 negative response: opcode={opcode:02X}")


class TP20DisconnectedException(TP20Exception):
    """Raised when trying to use a disconnected channel."""
    pass

