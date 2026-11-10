"""Tests for OOXML (docx/xlsx/pptx) metadata extraction."""

from __future__ import annotations

from metascan.models import RiskLevel
from metascan.scanner import scan_file


def _values(report):
    return {item.name: item.value for item in report.fields}


def test_docx_extracts_core_and_app_properties(docx_file):
    report = scan_file(docx_file, use_exiftool=False)
    values = _values(report)

    assert report.file_type == "docx"
    assert report.error is None
    assert values["Creator"] == "Carlos Mendes"
    assert values["LastModifiedBy"] == "joao.souza"
    assert values["Title"] == "Proposta Comercial"
    assert values["Created"] == "2024-03-10T09:00:00Z"
    assert values["Modified"] == "2024-03-12T18:22:00Z"
    assert values["Application"] == "Microsoft Office Word"
    assert values["AppVersion"] == "16.0000"
    assert values["Company"] == "Exemplo Ltda"


def test_xlsx_and_pptx_are_detected_and_parsed(xlsx_file, pptx_file):
    spreadsheet = scan_file(xlsx_file, use_exiftool=False)
    deck = scan_file(pptx_file, use_exiftool=False)

    assert spreadsheet.file_type == "xlsx"
    assert deck.file_type == "pptx"
    assert _values(spreadsheet)["Title"] == "Planilha de Custos"
    assert _values(deck)["Title"] == "Apresentacao Interna"
    assert _values(spreadsheet)["Creator"] == "Carlos Mendes"
    assert _values(deck)["LastModifiedBy"] == "joao.souza"


def test_office_identity_fields_raise_medium_risk(docx_file):
    report = scan_file(docx_file, use_exiftool=False)
    codes = {item.code for item in report.risks}

    assert report.risk_level is RiskLevel.MEDIUM
    assert "AUTHOR_NAME" in codes
    assert "SOFTWARE_VERSION" in codes
