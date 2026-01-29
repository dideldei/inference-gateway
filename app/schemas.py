"""Minimal request/response schemas for validation."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Error detail structure for upstream errors."""
    
    type: str = Field(description="Error type identifier")
    message: str = Field(description="Human-readable error message")


class ErrorResponse(BaseModel):
    """Structured error response format."""
    
    error: ErrorDetail = Field(description="Error details")
    upstream: str | None = Field(default=None, description="Upstream URL that failed")
