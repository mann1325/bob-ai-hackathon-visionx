import io
import logging
from typing import Optional, Tuple
import pypdf
import docx

logger = logging.getLogger(__name__)


class TextExtractionError(Exception):
    """Base exception for text extraction errors."""
    pass


class UnsupportedFormatError(TextExtractionError):
    """Raised when the document format is not supported."""
    pass


class CorruptedFileError(TextExtractionError):
    """Raised when the document file is corrupted or cannot be parsed."""
    pass


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx",
    "text/plain": "txt",
    "application/octet-stream": None,  # Will fallback to extension and magic bytes
}


def detect_file_type(filename: str, content: bytes, content_type: Optional[str] = None) -> str:
    """
    Detect and validate the file type using filename extension and magic bytes.
    Returns normalized file_type: 'pdf', 'docx', or 'txt'.
    Raises UnsupportedFormatError if unsupported.
    """
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported file extension '{ext}'. Allowed extensions: .pdf, .docx, .txt"
        )

    # Validate magic bytes / signatures
    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise CorruptedFileError("File does not have a valid PDF signature header.")
        return "pdf"

    elif ext == ".docx":
        # DOCX is an OpenXML ZIP archive
        if not content.startswith(b"PK\x03\x04"):
            raise CorruptedFileError("File does not have a valid DOCX/ZIP signature header.")
        return "docx"

    elif ext == ".txt":
        # Check for binary null bytes that indicate a raw binary file rather than plain text
        if b"\x00" in content[:1024]:
            raise CorruptedFileError("Text file appears to contain binary data.")
        return "txt"

    raise UnsupportedFormatError(f"Unsupported document format for '{filename}'.")


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF content bytes."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                # Try decrypting with empty password if possible
                reader.decrypt("")
            except Exception:
                raise CorruptedFileError("PDF file is password protected or encrypted.")

        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())

        extracted = "\n\n".join(text_parts).strip()
        return extracted
    except (CorruptedFileError, UnsupportedFormatError):
        raise
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", type(exc).__name__)
        raise CorruptedFileError(f"Failed to parse PDF document: {exc}") from exc


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX content bytes."""
    try:
        doc = docx.Document(io.BytesIO(content))
        text_parts = []

        for p in doc.paragraphs:
            if p.text and p.text.strip():
                text_parts.append(p.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_parts.append(" | ".join(row_text))

        extracted = "\n\n".join(text_parts).strip()
        return extracted
    except Exception as exc:
        logger.warning("DOCX extraction failed: %s", type(exc).__name__)
        raise CorruptedFileError(f"Failed to parse DOCX document: {exc}") from exc


def extract_text_from_txt(content: bytes) -> str:
    """Extract text from TXT content bytes with encoding fallback."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return content.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    raise CorruptedFileError("Failed to decode text file with supported character encodings.")


def extract_text(filename: str, content: bytes, content_type: Optional[str] = None) -> Tuple[str, str]:
    """
    Extract text from file bytes based on detected file type.
    Returns tuple of (file_type, extracted_text).
    """
    file_type = detect_file_type(filename, content, content_type)

    if file_type == "pdf":
        extracted_text = extract_text_from_pdf(content)
    elif file_type == "docx":
        extracted_text = extract_text_from_docx(content)
    elif file_type == "txt":
        extracted_text = extract_text_from_txt(content)
    else:
        raise UnsupportedFormatError(f"Unsupported file type: {file_type}")

    return file_type, extracted_text
