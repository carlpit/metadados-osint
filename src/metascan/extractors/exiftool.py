"""Optional enrichment via a local ExifTool binary.

Nothing is sent over the network. If the binary is missing or fails, the
caller simply keeps the pure-Python extraction result.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from metascan.models import Field

logger = logging.getLogger(__name__)

SKIP_KEYS = {
    "SourceFile",
    "ExifToolVersion",
    "FileName",
    "Directory",
    "FileSize",
    "FileModifyDate",
    "FileAccessDate",
    "FileInodeChangeDate",
    "FilePermissions",
    "FileType",
    "FileTypeExtension",
    "MIMEType",
    "ImageWidth",
    "ImageHeight",
    "ImageSize",
    "Megapixels",
    "EncodingProcess",
    "BitsPerSample",
    "ColorComponents",
    "YCbCrSubSampling",
}


def exiftool_available() -> bool:
    """Return True when an ``exiftool`` executable is on PATH."""

    return shutil.which("exiftool") is not None


def extract_exiftool_fields(path: Path, timeout: float = 20.0) -> list[Field]:
    """Return extra fields discovered by ExifTool, or an empty list."""

    binary = shutil.which("exiftool")
    if binary is None:
        return []

    try:
        completed = subprocess.run(  # noqa: S603 - fixed executable lookup via shutil.which
            [binary, "-j", "-n", "-G1", "--", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("exiftool failed for %s: %s", path, exc)
        return []

    if completed.returncode != 0 or not completed.stdout.strip():
        logger.debug("exiftool returned no data for %s: %s", path, completed.stderr.strip())
        return []

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        logger.debug("exiftool produced invalid JSON for %s", path)
        return []

    if not payload or not isinstance(payload, list) or not isinstance(payload[0], dict):
        return []

    fields: list[Field] = []
    for raw_key, value in payload[0].items():
        short_key = raw_key.split(":")[-1] if ":" in raw_key else raw_key
        if short_key in SKIP_KEYS or raw_key in SKIP_KEYS or value in (None, "", []):
            continue
        text = str(value).strip()
        if not text:
            continue
        fields.append(
            Field(
                name=short_key,
                value=text[:2000],
                category=_category_for(short_key),
                raw_key=f"exiftool:{raw_key}",
            )
        )
    return fields


def _category_for(name: str) -> str:
    key = name.lower().replace(" ", "")
    if "serial" in key:
        return "serial"
    identity = {
        "artist",
        "author",
        "creator",
        "lastmodifiedby",
        "ownername",
        "cameraownername",
        "copyright",
        "company",
    }
    if key in identity:
        return "identity"
    if key in {"software", "producer", "application", "appversion", "firmwareversion"}:
        return "software"
    if key in {"make", "model", "lensmodel", "lensmake", "uniquecameramodel"}:
        return "device"
    if key in {"hostcomputer"}:
        return "system"
    if "date" in key or "time" in key:
        return "timestamps"
    if key.startswith("gps") or key in {"latitude", "longitude"}:
        return "gps"
    return "other"
