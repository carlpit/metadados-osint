"""Extract document information from PDF files."""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from metascan.models import Field, GPSData
from metascan.textutil import as_str

logger = logging.getLogger(__name__)

# PDF "/Creator" is almost always the authoring application, not a person.
# "/Author" is the human-facing identity field.
_FIELD_MAP = {
    "/Author": ("Author", "identity"),
    "/Creator": ("Creator", "software"),
    "/Producer": ("Producer", "software"),
    "/Title": ("Title", "document"),
    "/Subject": ("Subject", "document"),
    "/Keywords": ("Keywords", "document"),
    "/CreationDate": ("CreationDate", "timestamps"),
    "/ModDate": ("ModDate", "timestamps"),
    "/Trapped": ("Trapped", "other"),
}


def extract_pdf(path: Path) -> tuple[list[Field], GPSData | None]:
    """Return document-info fields from a PDF file."""

    try:
        reader = PdfReader(str(path))
        metadata = reader.metadata
    except PdfReadError as exc:
        raise ValueError(f"PDF inválido ou corrompido: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"não foi possível ler o PDF: {exc}") from exc

    if metadata is None:
        return [], None

    fields: list[Field] = []
    raw_items = _metadata_items(metadata)
    for key, value in raw_items:
        text = as_str(value)
        if not text:
            continue
        name, category = _FIELD_MAP.get(key, (key.lstrip("/"), _guess_category(key)))
        fields.append(Field(name=name, value=text, category=category, raw_key=key))
    return fields, None


def _metadata_items(metadata: object) -> list[tuple[str, object]]:
    items: list[tuple[str, object]] = []
    if hasattr(metadata, "items"):
        try:
            items.extend((str(key), value) for key, value in metadata.items())  # type: ignore[attr-defined]
            return items
        except Exception:  # noqa: BLE001
            logger.debug("Falling back to named PDF metadata attributes")

    for attr, key in (
        ("author", "/Author"),
        ("creator", "/Creator"),
        ("producer", "/Producer"),
        ("title", "/Title"),
        ("subject", "/Subject"),
        ("creation_date", "/CreationDate"),
        ("modification_date", "/ModDate"),
    ):
        value = getattr(metadata, attr, None)
        if value is not None:
            items.append((key, value))
    return items


def _guess_category(key: str) -> str:
    lowered = key.lower()
    if "author" in lowered:
        return "identity"
    if any(token in lowered for token in ("creator", "producer", "application")):
        return "software"
    if "date" in lowered:
        return "timestamps"
    return "document"
