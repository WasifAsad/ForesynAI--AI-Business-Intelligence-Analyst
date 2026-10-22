from fastapi import APIRouter, File, UploadFile, status

from app.schemas.responses import DatasetPreviewResponse, APIErrorResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/api/dataset", tags=["Dataset Operations"])


@router.post(
    "/upload-preview",
    response_model=DatasetPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload dataset and generate preview",
    description="Validates a CSV or Excel file, reads it into memory, and returns dimensions and first 5 rows.",
    responses={
        400: {"model": APIErrorResponse, "description": "Invalid format, empty file, or malformed data"},
        413: {"model": APIErrorResponse, "description": "File exceeds size limit"},
        422: {"model": APIErrorResponse, "description": "Unprocessable file contents"}
    }
)
async def upload_and_preview(file: UploadFile = File(...)) -> DatasetPreviewResponse:
    """
    Ingests an uploaded CSV or XLSX file and generates a structured preview.
    """
    filename, df = await FileService.validate_and_read(file)
    return FileService.generate_preview(filename=filename, df=df)
