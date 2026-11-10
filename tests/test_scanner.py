"""Tests for path collection and scan orchestration."""

from __future__ import annotations

import pytest

from metascan.models import RiskLevel
from metascan.scanner import collect_paths, scan_file, scan_paths


def test_collect_paths_non_recursive_skips_nested(sample_tree):
    files = collect_paths([sample_tree], recursive=False)
    names = {path.name for path in files}

    assert "foto_gps.jpg" in names
    assert "notas.txt" in names
    assert "relatorio.pdf" not in names


def test_collect_paths_recursive_includes_nested(sample_tree):
    files = collect_paths([sample_tree], recursive=True)
    names = {path.name for path in files}

    assert {"foto_gps.jpg", "relatorio.pdf", "proposta.docx", "notas.txt"} <= names


def test_collect_paths_missing_target(tmp_path):
    with pytest.raises(FileNotFoundError):
        collect_paths([tmp_path / "ausente"], recursive=False)


def test_scan_unknown_type(tmp_path):
    blob = tmp_path / "notas.txt"
    blob.write_text("sem metadados", encoding="utf-8")
    report = scan_file(blob, use_exiftool=False)

    assert report.file_type == "unknown"
    assert report.error is not None
    assert report.risk_level is RiskLevel.NONE


def test_scan_paths_aggregate(jpeg_with_exif, pdf_with_metadata):
    result = scan_paths([jpeg_with_exif, pdf_with_metadata], use_exiftool=False)

    assert result.scanned == 2
    assert result.errors == 0
    assert result.highest_risk is RiskLevel.HIGH
