"""Text extraction for locally uploaded PDF and DOCX files."""

from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZipFile

import pymupdf
from docx import Document as WordDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError

from app.core.config import settings
from app.document_processing.chunking import normalize_text

MAX_PDF_PAGES = 1000
MAX_DOCX_EXPANDED_BYTES = 100 * 1024 * 1024


class DocumentExtractionError(ValueError):
    """Raised when a supported file cannot provide usable embedded text."""


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    page_ranges: list[tuple[int, int]] | None = None


def extract_pdf(data: bytes) -> ExtractedDocument:
    """Extract embedded page text and use local Tesseract for scanned pages."""
    if b"%PDF-" not in data[:1024]:
        raise DocumentExtractionError("The uploaded file does not have a valid PDF header.")

    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise DocumentExtractionError("Password-protected PDFs are not supported yet.")
            if pdf.page_count == 0:
                raise DocumentExtractionError("The PDF has no pages.")
            if pdf.page_count > MAX_PDF_PAGES:
                raise DocumentExtractionError(
                    f"PDFs are limited to {MAX_PDF_PAGES} pages per upload."
                )

            page_texts = []
            for page in pdf:
                text = normalize_text(page.get_text("text", sort=True))
                if not text and settings.ocr_enabled and page.get_images(full=True):
                    try:
                        ocr_text_page = page.get_textpage_ocr(
                            language=settings.ocr_language,
                            dpi=settings.ocr_dpi,
                            full=True,
                            tessdata=str(settings.ocr_tessdata_path)
                            if settings.ocr_tessdata_path
                            else None,
                        )
                        text = normalize_text(
                            page.get_text("text", textpage=ocr_text_page, sort=True)
                        )
                    except (RuntimeError, ValueError, OSError) as exception:
                        raise DocumentExtractionError(
                            "Could not OCR this scanned PDF page. Install Tesseract with the requested language data, or disable OCR with LAWSPHERE_OCR_ENABLED=false."
                        ) from exception
                page_texts.append(text)
    except DocumentExtractionError:
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exception:
        raise DocumentExtractionError("Could not read this PDF file.") from exception

    if not any(page_texts):
        if settings.ocr_enabled:
            raise DocumentExtractionError("No readable text was found, even after OCR.")
        raise DocumentExtractionError(
            "No embedded text was found. Enable OCR and install Tesseract to read scanned PDFs."
        )

    parts: list[str] = []
    page_ranges: list[tuple[int, int]] = []
    offset = 0
    for index, page_text in enumerate(page_texts):
        page_ranges.append((offset, offset + len(page_text)))
        parts.append(page_text)
        offset += len(page_text)
        if index < len(page_texts) - 1:
            separator = "\n\f\n"
            parts.append(separator)
            offset += len(separator)

    return ExtractedDocument(text="".join(parts), page_ranges=page_ranges)


def extract_docx(data: bytes) -> ExtractedDocument:
    """Extract paragraphs and tables in their original document-body order."""
    try:
        with ZipFile(BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise DocumentExtractionError("The DOCX package is missing its main document part.")
            expanded_size = sum(member.file_size for member in archive.infolist())
            if expanded_size > MAX_DOCX_EXPANDED_BYTES:
                raise DocumentExtractionError("The DOCX expands beyond the 100 MB processing limit.")
        document = WordDocument(BytesIO(data))
    except DocumentExtractionError:
        raise
    except (BadZipFile, KeyError, ValueError, OSError, PackageNotFoundError, XMLSyntaxError) as exception:
        raise DocumentExtractionError("Could not read this DOCX file.") from exception

    blocks: list[str] = []
    for item in document.element.body.iterchildren():
        if isinstance(item, CT_P):
            paragraph = Paragraph(item, document)
            paragraph_text = paragraph.text.strip()
            if paragraph_text:
                blocks.append(paragraph_text)
        elif isinstance(item, CT_Tbl):
            table = Table(item, document)
            rows = [
                " | ".join(cell.text.strip() for cell in row.cells)
                for row in table.rows
            ]
            table_text = "\n".join(row for row in rows if row.strip(" |"))
            if table_text:
                blocks.append(table_text)

    text = normalize_text("\n\n".join(blocks))
    if not text:
        raise DocumentExtractionError("No readable text was found in this DOCX file.")
    return ExtractedDocument(text=text)
