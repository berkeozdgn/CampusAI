import hashlib
from typing import Any
from pypdf import PdfReader

def split_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size, overlap değerinden büyük olmalı.")
    chunks = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks

def read_pdf(uploaded_file: Any) -> list[dict[str, Any]]:
    uploaded_file.seek(0)
    reader = PdfReader(uploaded_file)
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages.append({"page": page_number, "text": text.strip()})
    return pages

def create_file_id(uploaded_file: Any) -> str:
    return hashlib.sha256(uploaded_file.getvalue()).hexdigest()[:16]

def create_collection_name(uploaded_files: list[Any]) -> str:
    file_ids = sorted(create_file_id(file) for file in uploaded_files)
    combined_value = "_".join(file_ids)
    collection_id = hashlib.sha256(
        combined_value.encode("utf-8")
    ).hexdigest()[:16]
    return f"pdfs_{collection_id}"
