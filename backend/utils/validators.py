from fastapi import HTTPException, UploadFile
import fitz

MAX_FILE_SIZE_MB = 20
MAX_PAGES = 50
ALLOWED_TYPES = ["application/pdf"]


async def validate_file(file: UploadFile, label: str) -> bytes:
    """Validate file type, size, and PDF integrity. Returns file bytes."""

    # Check content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: Only PDF files are accepted. Got: {file.content_type}"
        )

    # Read bytes
    file_bytes = await file.read()

    # Check size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: File too large ({size_mb:.1f}MB). Max allowed: {MAX_FILE_SIZE_MB}MB"
        )

    # Check PDF integrity
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = doc.page_count
        doc.close()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: File appears to be corrupted or is not a valid PDF."
        )

    # Check page count
    if page_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: PDF has no pages."
        )

    if page_count > MAX_PAGES:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: PDF has {page_count} pages. Max allowed: {MAX_PAGES}"
        )

    return file_bytes


def validate_total_marks(total_marks: int):
    if total_marks <= 0 or total_marks > 1000:
        raise HTTPException(
            status_code=400,
            detail=f"Total marks must be between 1 and 1000. Got: {total_marks}"
        )


def validate_student_count(count: int):
    if count == 0:
        raise HTTPException(
            status_code=400,
            detail="No student answer sheets provided."
        )
    if count > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Too many student sheets ({count}). Max 100 per batch."
        )
