"""Tests for creating metadata-stripped copies of images."""

from __future__ import annotations

import hashlib
from pathlib import Path

from metascan.models import RiskLevel
from metascan.scanner import scan_file
from metascan.strip import StripError, cleaned_destination, strip_image


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_strip_creates_copy_and_preserves_original(jpeg_with_exif, tmp_path):
    original_hash = _sha256(jpeg_with_exif)
    destination = tmp_path / "saida" / "foto_gps_clean.jpg"

    result = strip_image(jpeg_with_exif, destination=destination)

    assert result == destination
    assert destination.is_file()
    assert _sha256(jpeg_with_exif) == original_hash
    assert destination.read_bytes() != jpeg_with_exif.read_bytes()


def test_stripped_jpeg_has_no_gps_or_serial(jpeg_with_exif, tmp_path):
    cleaned = strip_image(jpeg_with_exif, directory=tmp_path / "limpo")
    report = scan_file(cleaned, use_exiftool=False)
    codes = {item.code for item in report.risks}

    assert report.gps is None
    assert "GPS_COORDINATES" not in codes
    assert "DEVICE_SERIAL" not in codes
    assert report.risk_level in {RiskLevel.NONE, RiskLevel.LOW}


def test_strip_refuses_non_image(pdf_with_metadata):
    try:
        strip_image(pdf_with_metadata)
    except StripError as exc:
        assert "imagens" in str(exc)
    else:
        raise AssertionError("expected StripError for PDF input")


def test_cleaned_destination_never_points_at_source(jpeg_with_exif):
    dest = cleaned_destination(jpeg_with_exif, suffix="_clean")
    assert dest != jpeg_with_exif
    assert dest.name.endswith("_clean.jpg")
