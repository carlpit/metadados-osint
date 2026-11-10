"""Extract EXIF and related metadata from raster images."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import GPSTAGS, IFD, TAGS

from metascan.models import Field, GPSData, build_gps
from metascan.textutil import as_str, decode_xp, dms_to_decimal

logger = logging.getLogger(__name__)

# Categories used later by the risk engine.
IDENTITY_KEYS = {
    "artist",
    "author",
    "xpauthor",
    "copyright",
    "cameraownername",
    "ownername",
    "by-line",
    "credit",
    "contact",
}
SERIAL_KEYS = {
    "bodyserialnumber",
    "cameraserialnumber",
    "internalserialnumber",
    "serialnumber",
    "lensserialnumber",
}
SOFTWARE_KEYS = {"software", "processingsoftware", "firmwareversion"}
DEVICE_KEYS = {
    "make",
    "model",
    "uniquecameramodel",
    "lensmodel",
    "lensmake",
    "lensid",
    "uniqueid",
}
SYSTEM_KEYS = {"hostcomputer"}
TIMESTAMP_KEYS = {
    "datetime",
    "datetimeoriginal",
    "datetimedigitized",
    "offsettime",
    "offsettimeoriginal",
    "offsettimedigitized",
    "subsectime",
    "subsectimeoriginal",
    "subsectimedigitized",
    "gpsdatestamp",
    "gpstimestamp",
}
XP_KEYS = {"xpauthor", "xpcomment", "xpkeywords", "xpsubject", "xptitle"}

# Tags that belong to GPS and should not be duplicated as generic fields
# once a structured GPSData object has been built. Remaining GPS tags
# (altitude, timestamp, etc.) are still surfaced.
GPS_CORE_KEYS = {
    "gpslatitude",
    "gpslatituderef",
    "gpslongitude",
    "gpslongituderef",
}


def _maybe_register_heif() -> None:
    try:
        from pillow_heif import register_heif_opener
    except ImportError:
        return
    register_heif_opener()


_maybe_register_heif()


def extract_image(path: Path) -> tuple[list[Field], GPSData | None]:
    """Return metadata fields and optional GPS from an image file."""

    fields: list[Field] = []
    gps: GPSData | None = None
    try:
        with Image.open(path) as image:
            fields.extend(_info_fields(image))
            exif = image.getexif()
            if exif:
                mapped, gps = _parse_exif(exif)
                fields.extend(mapped)
    except UnidentifiedImageError as exc:
        raise ValueError(f"arquivo de imagem não reconhecido: {path.name}") from exc
    except OSError as exc:
        raise ValueError(f"não foi possível ler a imagem: {exc}") from exc
    return _dedupe(fields), gps


def _info_fields(image: Image.Image) -> list[Field]:
    """Collect textual chunks stored outside the EXIF IFD (common in PNG)."""

    fields: list[Field] = []
    info = image.info or {}
    skip = {
        "exif",
        "icc_profile",
        "xmp",
        "xml",
        "photoshop",
        "rawprofile",
        "dpi",
        "jfif",
        "jfif_version",
        "jfif_unit",
        "jfif_density",
        "progressive",
        "progression",
        "adobe",
        "adobe_transform",
    }
    for key, value in info.items():
        if key.lower() in skip or value in (None, "", b""):
            continue
        if isinstance(value, (bytes, bytearray)) and len(value) > 256:
            continue
        text = as_str(value)
        if not text:
            continue
        fields.append(
            Field(
                name=str(key),
                value=text,
                category=_category_for(str(key)),
                raw_key=f"info:{key}",
            )
        )
    return fields


def _parse_exif(exif: Any) -> tuple[list[Field], GPSData | None]:
    fields: list[Field] = []
    gps_ifd: dict[int, Any] = {}

    for tag_id, value in exif.items():
        name = TAGS.get(tag_id, str(tag_id))
        if name in {"GPSInfo", "MakerNote", "PrintImageMatching", "ExifOffset"}:
            continue
        text = _stringify_tag(name, value)
        if not text:
            continue
        fields.append(
            Field(
                name=name,
                value=text,
                category=_category_for(name),
                raw_key=str(tag_id),
            )
        )

    for ifd_id in (IFD.Exif, IFD.Interop):
        try:
            nested = exif.get_ifd(ifd_id)
        except (KeyError, OSError, ValueError):
            continue
        for tag_id, value in nested.items():
            name = TAGS.get(tag_id, str(tag_id))
            if name in {"MakerNote", "SceneType"}:
                continue
            text = _stringify_tag(name, value)
            if not text:
                continue
            fields.append(
                Field(
                    name=name,
                    value=text,
                    category=_category_for(name),
                    raw_key=f"exif:{tag_id}",
                )
            )

    try:
        raw_gps = exif.get_ifd(IFD.GPSInfo)
    except (KeyError, OSError, ValueError):
        raw_gps = {}
    if raw_gps:
        gps_ifd = dict(raw_gps)

    gps = _gps_from_ifd(gps_ifd) if gps_ifd else None
    for tag_id, value in gps_ifd.items():
        name = GPSTAGS.get(tag_id, f"GPSTag_{tag_id}")
        if name.lower() in GPS_CORE_KEYS and gps is not None:
            continue
        text = _stringify_tag(name, value)
        if not text:
            continue
        fields.append(
            Field(
                name=name,
                value=text,
                category="gps" if name.lower().startswith("gps") else "other",
                raw_key=f"gps:{tag_id}",
            )
        )
    return fields, gps


def _gps_from_ifd(gps_ifd: dict[int, Any]) -> GPSData | None:
    named = {GPSTAGS.get(key, str(key)): value for key, value in gps_ifd.items()}
    lat = named.get("GPSLatitude")
    lon = named.get("GPSLongitude")
    lat_ref = as_str(named.get("GPSLatitudeRef") or "N") or "N"
    lon_ref = as_str(named.get("GPSLongitudeRef") or "E") or "E"
    if not lat or not lon:
        return None
    try:
        latitude = dms_to_decimal(lat, lat_ref)
        longitude = dms_to_decimal(lon, lon_ref)
    except (TypeError, ValueError, ZeroDivisionError, IndexError) as exc:
        logger.debug("Unable to parse GPS IFD: %s", exc)
        return None
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return None
    return build_gps(latitude, longitude)


def _stringify_tag(name: str, value: Any) -> str:
    if value is None or value == "":
        return ""
    if name.lower() in XP_KEYS:
        return decode_xp(value)
    if isinstance(value, (bytes, bytearray)) and len(value) > 512:
        return ""
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
        # Nested structures such as GPS version; render compactly.
        try:
            return " ".join(as_str(part) for part in value)
        except Exception:  # noqa: BLE001 - defensive, keep extraction going
            return as_str(value)
    text = as_str(value)
    return text[:2000]


def _category_for(name: str) -> str:
    key = name.lower().replace(" ", "")
    if key in IDENTITY_KEYS or key.startswith("xpauthor"):
        return "identity"
    if key in SERIAL_KEYS or "serial" in key:
        return "serial"
    if key in SOFTWARE_KEYS:
        return "software"
    if key in DEVICE_KEYS:
        return "device"
    if key in SYSTEM_KEYS:
        return "system"
    if key in TIMESTAMP_KEYS or key.startswith("date") or key.startswith("offsettime"):
        return "timestamps"
    if key.startswith("gps"):
        return "gps"
    return "other"


def _dedupe(fields: list[Field]) -> list[Field]:
    seen: set[tuple[str, str]] = set()
    unique: list[Field] = []
    for item in fields:
        marker = (item.name.lower(), item.value)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique
