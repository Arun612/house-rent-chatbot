# pdf_parser.py
import fitz  # PyMuPDF
import hashlib


def parse_pdf(file_bytes: bytes, filename: str) -> dict:
    """
    Extract text from a PDF file using PyMuPDF, page by page.

    Returns:
        {
            "doc_id":     str  — unique 12-char hex ID based on file content,
            "filename":   str,
            "page_count": int,
            "pages":      [{"page_num": int, "text": str}, ...]
        }
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    # Generate ID based on file content hash so same file = same ID always
    doc_id = hashlib.md5(file_bytes).hexdigest()[:12]
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        cleaned = text.strip()
        if cleaned:
            pages.append({
                "page_num": page_num + 1,
                "text": cleaned,
            })

    total_pages = len(doc)
    doc.close()

    return {
        "doc_id": doc_id,
        "filename": filename,
        "page_count": total_pages,
        "pages": pages,
    }
