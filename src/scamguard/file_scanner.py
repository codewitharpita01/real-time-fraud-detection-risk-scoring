from io import BytesIO
import os

import pymupdf as fitz
from PIL import Image, UnidentifiedImageError

from .config import MAX_PDF_PAGES, MAX_UPLOAD_BYTES


class FileScanError(ValueError):
    """Safe, user-facing upload validation or extraction error."""


def _check_size(data: bytes):
    if not data:
        raise FileScanError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise FileScanError("File is too large. The limit is 15 MB.")


def _ocr(image: Image.Image) -> str:
    try:
        import pytesseract
        return pytesseract.image_to_string(image, lang=os.getenv("SCAMSHIELD_OCR_LANG", "eng"))
    except ImportError as exc:
        raise FileScanError("Python OCR package is missing. Install dependencies and Tesseract OCR, or paste the text manually.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise FileScanError("OCR engine not found. Install Tesseract OCR and add it to PATH, or paste the text manually.") from exc
    except Exception as exc:
        raise FileScanError("OCR could not read this image. You can paste the message text manually.") from exc


def extract_image_text(data: bytes, filename: str) -> str:
    _check_size(data)
    if filename.lower().rsplit(".", 1)[-1] not in {"png", "jpg", "jpeg"}:
        raise FileScanError("Unsupported image type. Upload PNG, JPG, or JPEG.")
    try:
        image = Image.open(BytesIO(data))
        if image.format not in {"PNG", "JPEG"}:
            raise FileScanError("The file contents do not match a supported PNG or JPEG image.")
        image.verify()
        image = Image.open(BytesIO(data)).convert("RGB")
    except FileScanError:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise FileScanError("This image is invalid or damaged.") from exc
    text = _ocr(image).strip()
    if not text:
        raise FileScanError("No readable text was found. You can paste the message text manually.")
    return text


def extract_pdf_text(data: bytes, filename: str) -> str:
    _check_size(data)
    if not filename.lower().endswith(".pdf") or not data.startswith(b"%PDF-"):
        raise FileScanError("Upload a valid PDF file.")
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise FileScanError("This PDF is invalid or cannot be opened.") from exc
    try:
        if document.is_encrypted:
            raise FileScanError("Password-protected PDFs are not supported. Do not upload sensitive documents.")
        if document.page_count > MAX_PDF_PAGES:
            raise FileScanError("PDF exceeds the 20-page limit.")
        page_text = []
        for page in document:
            text = page.get_text("text").strip()
            if len(text) < 20:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
                text = _ocr(image).strip()
            if text:
                page_text.append(text)
        combined = "\n\n".join(page_text).strip()
        if not combined:
            raise FileScanError("No readable text was found in the PDF.")
        return combined
    finally:
        document.close()
