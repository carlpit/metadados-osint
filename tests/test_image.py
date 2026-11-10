"""Tests for image metadata extraction and GPS conversion."""

from __future__ import annotations

from metascan.models import RiskLevel
from metascan.scanner import scan_file
from tests.factories import SAMPLE_LATITUDE, SAMPLE_LONGITUDE


def _field_map(report):
    return {item.name.lower(): item.value for item in report.fields}


def test_jpeg_extracts_camera_software_and_serial(jpeg_with_exif):
    report = scan_file(jpeg_with_exif, use_exiftool=False)
    values = _field_map(report)

    assert report.file_type == "jpeg"
    assert report.error is None
    assert values.get("make") == "TestCam"
    assert values.get("model") == "Model X"
    assert values.get("software") == "MetaScan Test Suite"
    assert "SN12345678" in values.get("bodyserialnumber", "")


def test_jpeg_converts_gps_to_decimal_and_builds_map_links(jpeg_with_exif):
    report = scan_file(jpeg_with_exif, use_exiftool=False)

    assert report.gps is not None
    assert abs(report.gps.latitude - SAMPLE_LATITUDE) < 0.0002
    assert abs(report.gps.longitude - SAMPLE_LONGITUDE) < 0.0002
    coord = f"{report.gps.latitude},{report.gps.longitude}"
    assert coord in report.gps.google_maps
    assert "google.com/maps" in report.gps.google_maps
    assert "openstreetmap.org" in report.gps.openstreetmap
    assert f"mlat={report.gps.latitude}" in report.gps.openstreetmap


def test_jpeg_with_gps_and_serial_is_high_risk(jpeg_with_exif):
    report = scan_file(jpeg_with_exif, use_exiftool=False)
    codes = {item.code for item in report.risks}

    assert report.risk_level is RiskLevel.HIGH
    assert "GPS_COORDINATES" in codes
    assert "DEVICE_SERIAL" in codes
    assert "AUTHOR_NAME" in codes
    assert "SOFTWARE_VERSION" in codes
    assert "DEVICE_MODEL" in codes
    assert "HOST_COMPUTER" in codes


def test_plain_jpeg_has_no_gps(plain_jpeg):
    report = scan_file(plain_jpeg, use_exiftool=False)

    assert report.file_type == "jpeg"
    assert report.gps is None
    assert report.error is None
    assert report.risk_level in {RiskLevel.NONE, RiskLevel.LOW}


def test_png_extracts_text_chunks(png_with_text):
    report = scan_file(png_with_text, use_exiftool=False)
    values = _field_map(report)

    assert report.file_type == "png"
    assert values.get("author") == "Maria Costa"
    assert values.get("software") == "TestPNG 1.0"
    assert report.risk_level in {RiskLevel.MEDIUM, RiskLevel.LOW}
    assert any(item.code == "AUTHOR_NAME" for item in report.risks)
