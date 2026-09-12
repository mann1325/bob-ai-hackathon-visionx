import io
from pathlib import Path
import pytest
import pypdf
import docx
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_app_settings
from app.main import create_app
from database.models import DocumentUploadModel


def create_sample_pdf_bytes(text: str = "This is a sample regulatory safety report for Aspirin.") -> bytes:
    """Create valid PDF file bytes with text content using pypdf."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    
    # We can write minimal PDF using PdfWriter or direct stream
    # pypdf PdfWriter produces valid PDF bytes
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_sample_docx_bytes(text: str = "This is a safety document section for adverse events.") -> bytes:
    """Create valid DOCX file bytes with text content using python-docx."""
    doc = docx.Document()
    doc.add_paragraph(text)
    doc.add_paragraph("Section 2: Pharmacovigilance findings.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Adverse Reaction"
    table.rows[0].cells[1].text = "Haemorrhage"
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_upload_txt_document_success(client: TestClient, db_session, tmp_path):
    """Test uploading a valid TXT document."""
    app = client.app
    test_settings = Settings(upload_dir=str(tmp_path / "uploads"), max_upload_size_bytes=1024 * 1024)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    txt_content = b"Signal investigation notes: Observed increase in gastrointestinal events."
    files = {"file": ("investigation_notes.txt", txt_content, "text/plain")}

    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["document_id"].startswith("doc_")
    assert data["filename"] == "investigation_notes.txt"
    assert data["file_type"] == "txt"
    assert data["file_size_bytes"] == len(txt_content)
    assert "gastrointestinal events" in data["extracted_text_preview"]
    assert data["status"] == "extracted"

    # Verify database persistence
    saved_doc = db_session.query(DocumentUploadModel).filter_by(document_id=data["document_id"]).first()
    assert saved_doc is not None
    assert saved_doc.filename == "investigation_notes.txt"
    assert "gastrointestinal events" in saved_doc.extracted_text


def test_upload_docx_document_success(client: TestClient, db_session, tmp_path):
    """Test uploading a valid DOCX document and extracting paragraphs and tables."""
    app = client.app
    test_settings = Settings(upload_dir=str(tmp_path / "uploads"), max_upload_size_bytes=1024 * 1024)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    docx_bytes = create_sample_docx_bytes("Clinical safety overview regarding bleeding risk.")
    files = {"file": ("safety_overview.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["document_id"].startswith("doc_")
    assert data["filename"] == "safety_overview.docx"
    assert data["file_type"] == "docx"
    assert "Clinical safety overview" in data["extracted_text_preview"]
    assert "Haemorrhage" in data["extracted_text_preview"]


def test_upload_pdf_document_success(client: TestClient, db_session, tmp_path):
    """Test uploading a valid PDF document."""
    app = client.app
    test_settings = Settings(upload_dir=str(tmp_path / "uploads"), max_upload_size_bytes=1024 * 1024)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("label_update.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["document_id"].startswith("doc_")
    assert data["filename"] == "label_update.pdf"
    assert data["file_type"] == "pdf"
    assert data["status"] == "extracted"


def test_upload_with_signal_id_success(client: TestClient, db_session, tmp_path):
    """Test uploading document with an existing signal_id association."""
    app = client.app
    test_settings = Settings(upload_dir=str(tmp_path / "uploads"), max_upload_size_bytes=1024 * 1024)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    txt_content = b"Label review for Aspirin GI Bleed."
    files = {"file": ("label_aspirin.txt", txt_content, "text/plain")}
    data = {"signal_id": "sig-001"}

    response = client.post("/api/v1/documents/upload", files=files, data=data)
    assert response.status_code == 201
    resp_data = response.json()

    assert resp_data["signal_id"] == "sig-001"

    # Verify DB record
    saved_doc = db_session.query(DocumentUploadModel).filter_by(document_id=resp_data["document_id"]).first()
    assert saved_doc.signal_id == "sig-001"


def test_upload_with_invalid_signal_id(client: TestClient, tmp_path):
    """Test uploading document referencing a nonexistent signal_id."""
    app = client.app
    test_settings = Settings(upload_dir=str(tmp_path / "uploads"), max_upload_size_bytes=1024 * 1024)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    txt_content = b"Some notes."
    files = {"file": ("notes.txt", txt_content, "text/plain")}
    data = {"signal_id": "nonexistent-signal-999"}

    response = client.post("/api/v1/documents/upload", files=files, data=data)
    assert response.status_code == 404
    error = response.json()
    assert "not found" in error["error"]["message"].lower()


def test_upload_unsupported_file_extension(client: TestClient):
    """Test rejecting unsupported file format like .exe or .csv."""
    files = {"file": ("malicious.exe", b"MZ\x90\x00Binary content", "application/x-msdownload")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    error = response.json()
    assert "unsupported file extension" in error["error"]["message"].lower()


def test_upload_corrupted_pdf_header(client: TestClient):
    """Test rejecting file with .pdf extension but invalid magic bytes."""
    files = {"file": ("corrupted.pdf", b"NOT_A_REAL_PDF_HEADER_CONTENT", "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    error = response.json()
    assert "valid pdf signature" in error["error"]["message"].lower()


def test_upload_corrupted_docx_header(client: TestClient):
    """Test rejecting file with .docx extension but invalid zip header."""
    files = {"file": ("corrupted.docx", b"NOT_A_ZIP_ARCHIVE_DATA", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    error = response.json()
    assert "valid docx/zip signature" in error["error"]["message"].lower()


def test_upload_oversized_file(client: TestClient, tmp_path):
    """Test rejecting file that exceeds max_upload_size_bytes."""
    app = client.app
    # Set a tiny max upload limit (50 bytes)
    test_settings = Settings(upload_dir=str(tmp_path / "uploads"), max_upload_size_bytes=50)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    large_content = b"A" * 200
    files = {"file": ("large_doc.txt", large_content, "text/plain")}

    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 413
    error = response.json()
    assert "exceeds maximum allowed limit" in error["error"]["message"].lower()


def test_get_document_success(client: TestClient, tmp_path):
    """Test retrieving an uploaded document by ID."""
    app = client.app
    test_settings = Settings(upload_dir=str(tmp_path / "uploads"), max_upload_size_bytes=1024 * 1024)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    txt_content = b"Important pharmacovigilance documentation."
    files = {"file": ("important.txt", txt_content, "text/plain")}

    upload_resp = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_resp.json()["document_id"]

    get_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()

    assert get_data["document_id"] == doc_id
    assert get_data["filename"] == "important.txt"
    assert get_data["file_type"] == "txt"
    assert "Important pharmacovigilance documentation." in get_data["extracted_text_preview"]


def test_get_document_not_found(client: TestClient):
    """Test retrieving nonexistent document returns 404."""
    response = client.get("/api/v1/documents/doc_nonexistent_123")
    assert response.status_code == 404
    error = response.json()
    assert "not found" in error["error"]["message"].lower()


def test_storage_security_no_filesystem_leak(client: TestClient, tmp_path):
    """Test that responses and error details do not expose absolute server paths."""
    app = client.app
    test_settings = Settings(upload_dir=str(tmp_path / "secret_folder_123"), max_upload_size_bytes=1024 * 1024)
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    txt_content = b"Content to test storage security."
    files = {"file": ("test_leak.txt", txt_content, "text/plain")}

    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    # Verify no response fields contain internal paths
    assert "secret_folder_123" not in str(data)
    assert "storage_path" not in data
