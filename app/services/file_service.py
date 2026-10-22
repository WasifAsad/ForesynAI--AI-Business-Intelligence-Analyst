import io
import os
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
import numpy as np
import pandas as pd

from app.schemas.responses import DatasetPreviewResponse

# Configuration constants
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB default limit
CHUNK_SIZE_BYTES = 1024 * 1024          # Read 1 MB per chunk


class FileService:
    """Service responsible for validating, parsing, and previewing uploaded datasets."""

    @staticmethod
    async def validate_and_read(
        file: UploadFile,
        max_size: int = MAX_FILE_SIZE_BYTES
    ) -> Tuple[str, pd.DataFrame]:
        """
        Validates extension and size, then reads file bytes into a Pandas DataFrame.
        Does not persist files to disk.
        """
        filename = file.filename or ""
        _, ext = os.path.splitext(filename.lower())

        # 1. Validate file extension
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Only .csv and .xlsx files are supported."
            )

        # 2. Read in chunks to enforce size limits safely
        total_size = 0
        file_buffer = io.BytesIO()

        while chunk := await file.read(CHUNK_SIZE_BYTES):
            total_size += len(chunk)
            if total_size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {max_size // (1024 * 1024)} MB."
                )
            file_buffer.write(chunk)

        # 3. Check for empty file
        if total_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)."
            )

        # Rewind buffer pointer to start before reading with pandas
        file_buffer.seek(0)

        # 4. Parse content with Pandas
        try:
            if ext == ".csv":
                # Try UTF-8 first, fallback to latin-1 for international/legacy encodings
                try:
                    df = pd.read_csv(file_buffer)
                except UnicodeDecodeError:
                    file_buffer.seek(0)
                    df = pd.read_csv(file_buffer, encoding="latin-1")
            else:
                # Excel .xlsx
                df = pd.read_excel(file_buffer, engine="openpyxl")

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to parse dataset: {str(e)}"
            )

        # 5. Check if parsed DataFrame contains data
        if df.empty and len(df.columns) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The dataset contains no rows or columns."
            )

        return filename, df

    @staticmethod
    def generate_preview(
        filename: str,
        df: pd.DataFrame,
        limit: int = 5
    ) -> DatasetPreviewResponse:
        """
        Extracts structural metadata and the first `limit` rows.
        Converts NaNs and timestamps to JSON-safe representations.
        """
        row_count, column_count = df.shape
        columns = [str(col) for col in df.columns]

        # Take first 'limit' rows
        preview_df = df.head(limit).copy()

        # Convert timestamps / dates to string representation
        for col in preview_df.select_dtypes(include=["datetime", "datetimetz"]).columns:
            preview_df[col] = preview_df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

        # Replace NaN, NaT, and infinite values with None so JSON outputs null
        preview_df = preview_df.replace({np.nan: None})
        preview_records = preview_df.to_dict(orient="records")

        # Clean any remaining float NaNs that might persist in object columns
        for row in preview_records:
            for key, val in row.items():
                if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                    row[key] = None

        return DatasetPreviewResponse(
            filename=filename,
            row_count=row_count,
            column_count=column_count,
            columns=columns,
            preview_rows=preview_records
        )
