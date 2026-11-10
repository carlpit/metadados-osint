"""Tests for magic-byte and extension-based type detection."""

from __future__ import annotations

from metascan.detect import detect_type, sniff_header


def test_detects_jpeg_by_magic_even_with_wrong_extension(jpeg_with_exif, tmp_path):
    disguised = tmp_path / "foto.bin"
    disguised.write_bytes(jpeg_with_exif.read_bytes())

    assert sniff_header(disguised) == "jpeg"
    assert detect_type(disguised) == "jpeg"


def test_detects_pdf_and_office_by_content(pdf_with_metadata, docx_file, xlsx_file, pptx_file):
    assert detect_type(pdf_with_metadata) == "pdf"
    assert detect_type(docx_file) == "docx"
    assert detect_type(xlsx_file) == "xlsx"
    assert detect_type(pptx_file) == "pptx"


def test_unknown_extension_without_magic(tmp_path):
    path = tmp_path / "arquivo.xyz"
    path.write_text("conteudo solto", encoding="utf-8")

    assert detect_type(path) == "unknown"
