"""Shared pytest fixtures. Each test receives its own temporary files."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.factories import (
    create_docx,
    create_jpeg_with_exif,
    create_pdf_with_metadata,
    create_plain_jpeg,
    create_png_with_text,
    create_pptx,
    create_xlsx,
)


@pytest.fixture
def jpeg_with_exif(tmp_path: Path) -> Path:
    """JPEG containing GPS, serial, author and camera tags."""

    return create_jpeg_with_exif(tmp_path / "foto_gps.jpg")


@pytest.fixture
def plain_jpeg(tmp_path: Path) -> Path:
    """JPEG without EXIF."""

    return create_plain_jpeg(tmp_path / "foto_limpa.jpg")


@pytest.fixture
def png_with_text(tmp_path: Path) -> Path:
    """PNG with textual author/software chunks."""

    return create_png_with_text(tmp_path / "amostra.png")


@pytest.fixture
def pdf_with_metadata(tmp_path: Path) -> Path:
    """PDF with document-info metadata."""

    return create_pdf_with_metadata(tmp_path / "relatorio.pdf")


@pytest.fixture
def docx_file(tmp_path: Path) -> Path:
    """Sample DOCX with core and app properties."""

    return create_docx(tmp_path / "proposta.docx")


@pytest.fixture
def xlsx_file(tmp_path: Path) -> Path:
    """Sample XLSX with core and app properties."""

    return create_xlsx(tmp_path / "custos.xlsx")


@pytest.fixture
def pptx_file(tmp_path: Path) -> Path:
    """Sample PPTX with core and app properties."""

    return create_pptx(tmp_path / "apresentacao.pptx")


@pytest.fixture
def sample_tree(
    tmp_path: Path,
    jpeg_with_exif: Path,
    pdf_with_metadata: Path,
    docx_file: Path,
) -> Path:
    """Directory tree used to exercise recursive scans."""

    root = tmp_path / "acervo"
    nested = root / "docs"
    nested.mkdir(parents=True)
    (root / jpeg_with_exif.name).write_bytes(jpeg_with_exif.read_bytes())
    (nested / pdf_with_metadata.name).write_bytes(pdf_with_metadata.read_bytes())
    (nested / docx_file.name).write_bytes(docx_file.read_bytes())
    (root / "notas.txt").write_text("arquivo sem metadados estruturados\n", encoding="utf-8")
    return root
