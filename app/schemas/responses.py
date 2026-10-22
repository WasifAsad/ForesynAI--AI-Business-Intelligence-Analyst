from typing import Any, Dict, List
from pydantic import BaseModel, Field


class DatasetPreviewResponse(BaseModel):
    """Schema returned after validating and previewing an uploaded dataset."""
    filename: str = Field(..., description="Name of the uploaded file")
    row_count: int = Field(..., description="Total number of rows in the dataset")
    column_count: int = Field(..., description="Total number of columns in the dataset")
    columns: List[str] = Field(..., description="List of column names")
    preview_rows: List[Dict[str, Any]] = Field(
        ..., 
        description="First few rows formatted as key-value pairs (NaN values mapped to null)"
    )


class APIErrorResponse(BaseModel):
    """Standard error response format."""
    detail: str = Field(..., description="Description of the error encountered")
