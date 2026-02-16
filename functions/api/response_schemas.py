"""
Standardized response schemas for all API endpoints.
Using Pydantic models ensures compile-time validation of response structures.
"""
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field, model_validator


# Generic type variable for data payload
T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper with success flag and optional data/error.
    
    All endpoints should return this structure:
    - Success: {"success": true, "data": {...}}
    - Error: {"success": false, "error": "message"}
    
    Usage:
        # Success response
        return ApiResponse(success=True, data={"result": "value"}).model_dump()
        
        # Error response
        return ApiResponse(success=False, error="Something went wrong").model_dump()
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_response(self):
        """Ensure success responses have data and error responses have error message."""
        if self.success and self.data is None:
            raise ValueError("Success response must include 'data' field")
        if not self.success and self.error is None:
            raise ValueError("Error response must include 'error' field")
        if self.success and self.error is not None:
            raise ValueError("Success response should not include 'error' field")
        if not self.success and self.data is not None:
            raise ValueError("Error response should not include 'data' field")
        return self


class EmptyData(BaseModel):
    """Empty data object for responses that don't return specific data."""
    pass


# Specific response data models for different endpoints

class SummaryData(BaseModel):
    """Data model for summarize_snipe_logs endpoint."""
    summary: str = Field(..., description="AI-generated summary of reservation attempt")


class SnipeResultData(BaseModel):
    """Data model for run_snipe endpoint."""
    status: str = Field(..., description="Final status: 'done' or 'failed'")
    jobId: str = Field(..., description="Reservation job ID")
    resyToken: Optional[str] = Field(None, description="Resy confirmation token if successful")


class JobCreatedData(BaseModel):
    """Data model for create_snipe endpoint."""
    jobId: str = Field(..., description="Created reservation job ID")
    targetTimeIso: str = Field(..., description="ISO timestamp when snipe will execute")


class JobUpdatedData(BaseModel):
    """Data model for update_snipe endpoint."""
    jobId: str = Field(..., description="Updated reservation job ID")
    targetTimeIso: str = Field(..., description="ISO timestamp when snipe will execute")


class JobCancelledData(BaseModel):
    """Data model for cancel_snipe endpoint."""
    jobId: str = Field(..., description="Cancelled reservation job ID")


# Type aliases for common response types
SummaryResponse = ApiResponse[SummaryData]
SnipeResultResponse = ApiResponse[SnipeResultData]
JobCreatedResponse = ApiResponse[JobCreatedData]
JobUpdatedResponse = ApiResponse[JobUpdatedData]
JobCancelledResponse = ApiResponse[JobCancelledData]
EmptyResponse = ApiResponse[EmptyData]


def success_response(data: Any) -> Dict[str, Any]:
    """
    Helper to create a validated success response.
    
    Args:
        data: Response data (dict or Pydantic model)
        
    Returns:
        Validated response dict
        
    Raises:
        ValidationError if response structure is invalid
    """
    response = ApiResponse(success=True, data=data)
    return response.model_dump(exclude_none=True)


def error_response(error: str, status_code: int = 500) -> tuple[Dict[str, Any], int]:
    """
    Helper to create a validated error response with status code.
    
    Args:
        error: Error message
        status_code: HTTP status code (default 500)
        
    Returns:
        Tuple of (response_dict, status_code)
        
    Raises:
        ValidationError if response structure is invalid
    """
    response = ApiResponse(success=False, error=error)
    return response.model_dump(exclude_none=True), status_code
