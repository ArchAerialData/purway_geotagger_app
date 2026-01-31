from __future__ import annotations

class PurwayGeotaggerError(Exception):
    """Base exception for the application."""

class UserCancelledError(PurwayGeotaggerError):
    """Raised when user cancels an in-progress job."""

class ExifToolError(PurwayGeotaggerError):
    """Raised when ExifTool invocation fails."""

class CorrelationError(PurwayGeotaggerError):
    """Raised when a photo cannot be reliably correlated to a CSV row."""
