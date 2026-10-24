"""Plain-text extraction from resume files."""

import zipfile
from pathlib import Path
from xml.etree import ElementTree

_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        root = ElementTree.fromstring(zf.read("word/document.xml"))
    paragraphs = []
    for para in root.iter(f"{_WORD_NS}p"):
        text = "".join(node.text or "" for node in para.iter(f"{_WORD_NS}t"))
        if text.strip():
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_text(file_path: str) -> str:
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"no file at {path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _pdf_text(path)
    elif suffix == ".docx":
        text = _docx_text(path)
    elif suffix in (".txt", ".md"):
        text = path.read_text(errors="replace")
    else:
        raise ValueError(f"unsupported resume format {suffix!r}; send a PDF, DOCX, TXT or MD file")
    if not text.strip():
        raise ValueError("no text found in the resume (is it a scanned image?)")
    return text
