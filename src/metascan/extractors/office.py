"""Extract core and app properties from OOXML Office documents.

Only well-known members inside the ZIP container are read
(``docProps/core.xml`` and ``docProps/app.xml``). Nothing is extracted to
disk, which avoids zip-slip issues, and the XML parser does not resolve
external entities.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from metascan.models import Field, GPSData

logger = logging.getLogger(__name__)

MAX_XML_BYTES = 1_048_576

NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
}

CORE_PATH = "docProps/core.xml"
APP_PATH = "docProps/app.xml"

CORE_FIELDS = (
    ("dc:title", "Title", "document"),
    ("dc:subject", "Subject", "document"),
    ("dc:description", "Description", "document"),
    ("dc:creator", "Creator", "identity"),
    ("cp:lastModifiedBy", "LastModifiedBy", "identity"),
    ("cp:revision", "Revision", "other"),
    ("cp:lastPrinted", "LastPrinted", "timestamps"),
    ("cp:category", "Category", "document"),
    ("cp:keywords", "Keywords", "document"),
    ("dcterms:created", "Created", "timestamps"),
    ("dcterms:modified", "Modified", "timestamps"),
)

APP_FIELDS = (
    ("ep:Application", "Application", "software"),
    ("ep:AppVersion", "AppVersion", "software"),
    ("ep:Company", "Company", "identity"),
    ("ep:Manager", "Manager", "identity"),
    ("ep:Template", "Template", "other"),
    ("ep:Pages", "Pages", "other"),
    ("ep:Words", "Words", "other"),
    ("ep:Slides", "Slides", "other"),
)


def extract_office(path: Path) -> tuple[list[Field], GPSData | None]:
    """Return core/app property fields from a DOCX, XLSX or PPTX file."""

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            fields: list[Field] = []
            if CORE_PATH in names:
                fields.extend(_parse_member(archive, CORE_PATH, CORE_FIELDS))
            if APP_PATH in names:
                fields.extend(_parse_member(archive, APP_PATH, APP_FIELDS))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"documento Office inválido: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"não foi possível ler o documento: {exc}") from exc
    return fields, None


def _parse_member(
    archive: zipfile.ZipFile,
    member: str,
    spec: tuple[tuple[str, str, str], ...],
) -> list[Field]:
    try:
        info = archive.getinfo(member)
    except KeyError:
        return []
    if info.file_size > MAX_XML_BYTES:
        logger.warning("Skipping oversized OOXML member %s (%s bytes)", member, info.file_size)
        return []
    # Reject path traversal disguised as a stored member name.
    if Path(member).is_absolute() or ".." in Path(member).parts:
        logger.warning("Skipping suspicious OOXML member name: %s", member)
        return []

    with archive.open(member) as handle:
        raw = handle.read(MAX_XML_BYTES + 1)
    if len(raw) > MAX_XML_BYTES:
        return []

    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        logger.debug("Unable to parse %s: %s", member, exc)
        return []

    fields: list[Field] = []
    for xpath, name, category in spec:
        text = _first_text(root, xpath)
        if text:
            fields.append(Field(name=name, value=text, category=category, raw_key=xpath))
    return fields


def _first_text(root: ElementTree.Element, xpath: str) -> str:
    element = root.find(xpath, NS)
    if element is None or element.text is None:
        return ""
    return element.text.strip()
