from pathlib import Path
from typing import Any


def get_subject_documents(
    subject_path: str | Path,
) -> list[dict[str, Any]]:
    """
    Seçilen ders klasöründeki PDF dosyalarını listeler.
    """

    folder = Path(subject_path)

    if not folder.exists():
        return []

    documents: list[dict[str, Any]] = []

    for file_path in sorted(
        folder.glob("*.pdf"),
        key=lambda path: path.name.lower(),
    ):
        file_size = file_path.stat().st_size

        documents.append(
            {
                "name": file_path.name,
                "path": file_path,
                "size_bytes": file_size,
                "size_text": format_file_size(file_size),
                "modified_at": file_path.stat().st_mtime,
            }
        )

    return documents


def format_file_size(size_bytes: int) -> str:
    """
    Dosya boyutunu okunabilir biçime dönüştürür.
    """

    if size_bytes < 1024:
        return f"{size_bytes} B"

    size_kb = size_bytes / 1024

    if size_kb < 1024:
        return f"{size_kb:.1f} KB"

    size_mb = size_kb / 1024

    return f"{size_mb:.1f} MB"


def delete_document(
    subject_path: str | Path,
    file_name: str,
) -> bool:
    """
    Seçilen PDF dosyasını ders klasöründen siler.
    """

    folder = Path(subject_path)

    safe_file_name = Path(file_name).name
    file_path = folder / safe_file_name

    if not file_path.exists():
        return False

    if file_path.suffix.lower() != ".pdf":
        return False

    try:
        file_path.unlink()
        return True

    except OSError:
        return False


def count_subject_documents(
    subject_path: str | Path,
) -> int:
    """
    Seçilen dersteki PDF sayısını döndürür.
    """

    return len(
        get_subject_documents(subject_path)
    )


def get_total_pdf_count(
    pdf_root: str | Path,
) -> int:
    """
    Bütün derslerdeki toplam PDF sayısını döndürür.
    """

    root = Path(pdf_root)

    if not root.exists():
        return 0

    return sum(
        1
        for file_path in root.rglob("*.pdf")
        if file_path.is_file()
    )