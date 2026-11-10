"""Tests for report renderers."""

from __future__ import annotations

import json

from metascan.formatters import render
from metascan.scanner import scan_paths


def test_json_renderer_structure(jpeg_with_exif):
    result = scan_paths([jpeg_with_exif], use_exiftool=False)
    payload = json.loads(render(result, "json"))

    assert payload["scanned"] == 1
    assert "files" in payload
    assert payload["files"][0]["gps"]["google_maps"].startswith("https://")


def test_markdown_and_table_include_risks(jpeg_with_exif):
    result = scan_paths([jpeg_with_exif], use_exiftool=False)
    markdown = render(result, "markdown")
    table = render(result, "table")

    assert "Alertas de privacidade" in markdown
    assert "GPS_COORDINATES" in markdown
    assert jpeg_with_exif.name in table
    assert "openstreetmap.org" in table


def test_csv_has_one_row_per_field(pdf_with_metadata):
    result = scan_paths([pdf_with_metadata], use_exiftool=False)
    rows = render(result, "csv").strip().splitlines()

    assert rows[0].startswith("path,")
    assert len(rows) > 2
    assert any("Ana Silva" in row for row in rows)


def test_unsupported_format_raises(jpeg_with_exif):
    result = scan_paths([jpeg_with_exif], use_exiftool=False)
    try:
        render(result, "xml")
    except ValueError as exc:
        assert "não suportado" in str(exc)
    else:
        raise AssertionError("expected ValueError")
