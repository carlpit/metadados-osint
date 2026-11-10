"""Helpers that build synthetic sample files for the test suite."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import piexif
from PIL import Image
from pypdf import PdfWriter

# Example coordinates used only in generated fixtures (João Pessoa, PB).
SAMPLE_LATITUDE = -7.1195
SAMPLE_LONGITUDE = -34.8450


def to_dms(value: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Convert a decimal degree into an EXIF rational DMS triple."""

    absolute = abs(value)
    degrees = int(absolute)
    minutes_full = (absolute - degrees) * 60
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60
    return ((degrees, 1), (minutes, 1), (int(round(seconds * 10_000)), 10_000))


def create_jpeg_with_exif(path: Path) -> Path:
    """Write a JPEG that contains camera, software, serial and GPS tags."""

    image = Image.new("RGB", (120, 80), color=(32, 96, 160))
    zeroth_ifd = {
        piexif.ImageIFD.Make: b"TestCam",
        piexif.ImageIFD.Model: b"Model X",
        piexif.ImageIFD.Software: b"MetaScan Test Suite",
        piexif.ImageIFD.DateTime: b"2024:06:15 14:30:00",
        piexif.ImageIFD.Artist: b"Ana Silva",
        piexif.ImageIFD.Copyright: b"Ana Silva",
        piexif.ImageIFD.HostComputer: b"NOTEBOOK-ANA",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: b"2024:06:15 14:30:00",
        piexif.ExifIFD.BodySerialNumber: b"SN12345678",
        piexif.ExifIFD.LensModel: b"TestLens 35mm",
    }
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"S",
        piexif.GPSIFD.GPSLatitude: to_dms(SAMPLE_LATITUDE),
        piexif.GPSIFD.GPSLongitudeRef: b"W",
        piexif.GPSIFD.GPSLongitude: to_dms(SAMPLE_LONGITUDE),
        piexif.GPSIFD.GPSAltitudeRef: 0,
        piexif.GPSIFD.GPSAltitude: (1200, 1),
    }
    exif_bytes = piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd})
    image.save(path, "JPEG", exif=exif_bytes, quality=90)
    return path


def create_plain_jpeg(path: Path) -> Path:
    """Write a JPEG without EXIF data."""

    Image.new("RGB", (40, 30), color=(200, 40, 40)).save(path, "JPEG", quality=85)
    return path


def create_png_with_text(path: Path) -> Path:
    """Write a PNG that stores author/software text chunks."""

    from PIL.PngImagePlugin import PngInfo

    image = Image.new("RGB", (48, 32), color=(16, 140, 90))
    info = PngInfo()
    info.add_text("Author", "Maria Costa")
    info.add_text("Software", "TestPNG 1.0")
    image.save(path, "PNG", pnginfo=info)
    return path


def create_pdf_with_metadata(path: Path) -> Path:
    """Write a one-page PDF with standard document-info fields."""

    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_metadata(
        {
            "/Author": "Ana Silva",
            "/Creator": "Microsoft Word",
            "/Producer": "pypdf test suite",
            "/Title": "Relatorio Confidencial",
            "/Subject": "Documento de teste",
            "/CreationDate": "D:20240615143000-03'00'",
            "/ModDate": "D:20240616100000-03'00'",
        }
    )
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def create_office_document(
    path: Path,
    kind: str,
    *,
    creator: str = "Carlos Mendes",
    modified_by: str = "joao.souza",
    title: str = "Proposta Comercial",
    application: str = "Microsoft Office Word",
    app_version: str = "16.0000",
) -> Path:
    """Write a minimal OOXML file (docx, xlsx or pptx) with core/app props."""

    if kind == "docx":
        main_member = "word/document.xml"
        main_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Amostra</w:t></w:r></w:p></w:body></w:document>"
        )
        override = (
            ' Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document.main+xml"'
        )
    elif kind == "xlsx":
        main_member = "xl/workbook.xml"
        main_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheets><sheet name='Amostra' sheetId='1' r:id='rId1' "
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
            "</sheets></workbook>"
        )
        override = (
            ' Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument'
            '.spreadsheetml.sheet.main+xml"'
        )
        application = "Microsoft Excel"
    elif kind == "pptx":
        main_member = "ppt/presentation.xml"
        main_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            "</p:presentation>"
        )
        override = (
            ' Override PartName="/ppt/presentation.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument'
            '.presentationml.presentation.main+xml"'
        )
        application = "Microsoft PowerPoint"
    else:
        raise ValueError(f"unsupported office kind: {kind}")

    core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties
    xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title}</dc:title>
  <dc:subject>Documento de teste</dc:subject>
  <dc:creator>{creator}</dc:creator>
  <cp:lastModifiedBy>{modified_by}</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2024-03-10T09:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2024-03-12T18:22:00Z</dcterms:modified>
</cp:coreProperties>
"""
    app_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>{application}</Application>
  <AppVersion>{app_version}</AppVersion>
  <Company>Exemplo Ltda</Company>
</Properties>
"""
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument'
        '.extended-properties+xml"/>'
        f"<{override}/>"
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        f'Target="{main_member}"/>'
        "</Relationships>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr(main_member, main_xml)
        archive.writestr("docProps/core.xml", core_xml)
        archive.writestr("docProps/app.xml", app_xml)
    path.write_bytes(buffer.getvalue())
    return path


def create_docx(path: Path) -> Path:
    """Write a sample DOCX file."""

    return create_office_document(path, "docx")


def create_xlsx(path: Path) -> Path:
    """Write a sample XLSX file."""

    return create_office_document(path, "xlsx", title="Planilha de Custos")


def create_pptx(path: Path) -> Path:
    """Write a sample PPTX file."""

    return create_office_document(path, "pptx", title="Apresentacao Interna")
