import fitz
import base64


def extract_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        print(f"[PDF] Text extraction error: {e}")
        return ""


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[str]:
    """
    Convert all PDF pages to base64 JPEG images.
    DPI 200 gives good quality for handwriting recognition.
    Returns list of base64 strings.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        scale = dpi / 72  # 72 is default PDF DPI
        matrix = fitz.Matrix(scale, scale)

        for page in doc:
            pix = page.get_pixmap(matrix=matrix)
            img_bytes = pix.tobytes("jpeg")
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            images.append(b64)

        doc.close()
        return images
    except Exception as e:
        print(f"[PDF] Image conversion error: {e}")
        return []


def get_page_count(pdf_bytes: bytes) -> int:
    """Return number of pages in PDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = doc.page_count
        doc.close()
        return count
    except Exception:
        return 0


def pdf_page_to_image(pdf_bytes: bytes, page_number: int, dpi: int = 200) -> str | None:
    """
    Convert a single PDF page to base64 JPEG.
    page_number is 0-indexed.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_number >= doc.page_count:
            return None
        scale = dpi / 72
        matrix = fitz.Matrix(scale, scale)
        page = doc[page_number]
        pix = page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        doc.close()
        return b64
    except Exception as e:
        print(f"[PDF] Single page conversion error: {e}")
        return None
