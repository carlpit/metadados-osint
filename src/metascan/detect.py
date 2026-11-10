"""Identify file types by extension and magic bytes."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_TYPES = frozenset({"jpeg", "png", "tiff", "webp", "heic", "gif", "bmp"})
PDF_TYPES = frozenset({"pdf"})
OFFICE_TYPES = frozenset({"docx", "xlsx", "pptx"})
SUPPORTED_TYPES = IMAGE_TYPES | PDF_TYPES | OFFICE_TYPES

EXTENSION_MAP = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".jpe": "jpeg",
    ".png": "png",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".webp": "webp",
    ".heic": "heic",
    ".heif": "heic",
    ".gif": "gif",
    ".bmp": "bmp",
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
}

SKIP_DIR_NAMES = frozenset({".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "node_modules"})


def sniff_header(path: Path) -> str | None:
    """Return a type name based on the file header, if recognized."""

    with path.open("rb") as handle:
        header = handle.read(32)
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"%PDF"):
        return "pdf"
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if header.startswith(b"BM"):
        return "bmp"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in {b"heic", b"heif", b"mif1", b"msf1", b"heix", b"hevc"}:
            return "heic"
    if header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return office_subtype_from_zip(path)
    return None


def office_subtype_from_zip(path: Path) -> str | None:
    """Distinguish DOCX/XLSX/PPTX by well-known members inside the ZIP."""

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        logger.debug("File looks like ZIP but is not a valid archive: %s", path)
        return None
    if "word/document.xml" in names:
        return "docx"
    if "xl/workbook.xml" in names:
        return "xlsx"
    if "ppt/presentation.xml" in names:
        return "pptx"
    return None


def detect_type(path: Path) -> str:
    """Detect the file type, preferring magic bytes over the extension."""

    try:
        sniffed = sniff_header(path)
    except OSError as exc:
        logger.debug("Unable to sniff %s: %s", path, exc)
        sniffed = None
    if sniffed:
        return sniffed
    return EXTENSION_MAP.get(path.suffix.lower(), "unknown")


def is_supported(file_type: str) -> bool:
    """Return whether ``file_type`` can be analyzed."""

    return file_type in SUPPORTED_TYPES


def should_skip_dir(path: Path) -> bool:
    """Return True for VCS/cache directories that should not be walked."""

    return path.name in SKIP_DIR_NAMES
