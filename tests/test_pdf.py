"""Tests for PDF document-info extraction."""

from __future__ import annotations

from metascan.models import RiskLevel
from metascan.scanner import scan_file


def test_pdf_extracts_core_document_info(pdf_with_metadata):
    report = scan_file(pdf_with_metadata, use_exiftool=False)
    values = {item.name: item.value for item in report.fields}

    assert report.file_type == "pdf"
    assert report.error is None
    assert values["Author"] == "Ana Silva"
    assert values["Creator"] == "Microsoft Word"
    assert values["Producer"] == "pypdf test suite"
    assert values["Title"] == "Relatorio Confidencial"
    assert "CreationDate" in values
    assert "ModDate" in values


def test_pdf_author_is_medium_risk_and_creator_is_software(pdf_with_metadata):
    report = scan_file(pdf_with_metadata, use_exiftool=False)
    by_name = {item.name: item.category for item in report.fields}
    codes = {item.code for item in report.risks}

    assert by_name["Author"] == "identity"
    assert by_name["Creator"] == "software"
    assert by_name["Producer"] == "software"
    assert report.risk_level is RiskLevel.MEDIUM
    assert "AUTHOR_NAME" in codes
    assert "SOFTWARE_VERSION" in codes
    assert "GPS_COORDINATES" not in codes
