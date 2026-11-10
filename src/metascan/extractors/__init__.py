"""Format-specific metadata extractors."""

from __future__ import annotations

from pathlib import Path

from metascan.detect import IMAGE_TYPES, OFFICE_TYPES, PDF_TYPES, detect_type
from metascan.extractors.image import extract_image
from metascan.extractors.office import extract_office
from metascan.extractors.pdf import extract_pdf
from metascan.models import Field, FileReport, GPSData

ExtractorResult = tuple[list[Field], GPSData | None]


def extract_native(path: Path, file_type: str | None = None) -> ExtractorResult:
    """Extract metadata using the built-in pure-Python readers."""

    kind = file_type or detect_type(path)
    if kind in IMAGE_TYPES:
        return extract_image(path)
    if kind in PDF_TYPES:
        return extract_pdf(path)
    if kind in OFFICE_TYPES:
        return extract_office(path)
    return [], None


def empty_report(path: Path, file_type: str, error: str | None = None) -> FileReport:
    """Build a report for an unsupported or unreadable file."""

    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return FileReport(
        path=str(path),
        file_type=file_type,
        size_bytes=size,
        error=error,
    )
