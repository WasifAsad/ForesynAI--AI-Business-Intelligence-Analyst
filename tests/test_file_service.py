import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_valid_csv():
    """Verifies that a valid CSV is parsed and returns correct metadata and preview."""
    csv_content = b"product,revenue,quantity\nWidget A,100.5,10\nWidget B,200.0,5\n"
    response = client.post(
        "/api/dataset/upload-preview",
        files={"file": ("sales.csv", io.BytesIO(csv_content), "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sales.csv"
    assert data["row_count"] == 2
    assert data["column_count"] == 3
    assert data["columns"] == ["product", "revenue", "quantity"]
    assert len(data["preview_rows"]) == 2
    assert data["preview_rows"][0]["product"] == "Widget A"
    assert data["preview_rows"][0]["revenue"] == 100.5


def test_upload_valid_excel():
    """Verifies that a valid .xlsx file is parsed properly."""
    df = pd.DataFrame({
        "item": ["Alpha", "Beta"],
        "stock": [50, 100]
    })
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    response = client.post(
        "/api/dataset/upload-preview",
        files={"file": ("inventory.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "inventory.xlsx"
    assert data["row_count"] == 2
    assert data["columns"] == ["item", "stock"]


def test_upload_empty_file():
    """Verifies that an empty file (0 bytes) returns HTTP 400 Bad Request."""
    response = client.post(
        "/api/dataset/upload-preview",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_unsupported_extension():
    """Verifies that files with unapproved extensions (.txt, .json) are rejected."""
    response = client.post(
        "/api/dataset/upload-preview",
        files={"file": ("data.txt", io.BytesIO(b"some,data\n1,2"), "text/plain")}
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_size_limit_exceeded():
    """Verifies that a file exceeding the maximum size limit is rejected with HTTP 413."""
    # We test with a small mock limit using FileService directly or large payload
    from app.services.file_service import FileService
    from fastapi import HTTPException, UploadFile
    import asyncio

    dummy_file = UploadFile(
        filename="big.csv",
        file=io.BytesIO(b"a" * 200)
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(FileService.validate_and_read(dummy_file, max_size=100))

    assert exc_info.value.status_code == 413
    assert "exceeds maximum allowed size" in exc_info.value.detail


def test_csv_with_missing_values_returns_null_in_json():
    """Verifies that NaN values in a dataset serialize to JSON null without errors."""
    csv_content = b"name,price,category\nApple,1.5,Fruit\nBanana,,Fruit\nOrange,2.0,\n"
    response = client.post(
        "/api/dataset/upload-preview",
        files={"file": ("products.csv", io.BytesIO(csv_content), "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 3
    # Check that missing price for Banana is None (null in JSON)
    assert data["preview_rows"][1]["price"] is None
    # Check that missing category for Orange is None
    assert data["preview_rows"][2]["category"] is None
