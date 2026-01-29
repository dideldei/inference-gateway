"""Custom exceptions for the inference gateway core library."""


class GatewayError(Exception):
    """Base exception for all gateway errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AudioProcessingError(GatewayError):
    """Raised when audio preprocessing fails."""

    def __init__(self, message: str, error_type: str = "audio_processing_error"):
        self.error_type = error_type
        super().__init__(message)


class UpstreamError(GatewayError):
    """Base class for upstream-related errors."""

    def __init__(self, message: str, upstream: str | None = None):
        self.upstream = upstream
        super().__init__(message)


class UpstreamUnreachableError(UpstreamError):
    """Raised when the upstream server is unreachable."""

    pass


class UpstreamTimeoutError(UpstreamError):
    """Raised when a request to the upstream server times out."""

    pass


class ConfigurationError(GatewayError):
    """Raised when there is a configuration problem."""

    pass


class InvalidRequestError(GatewayError):
    """Raised when a request is malformed or invalid."""

    pass
