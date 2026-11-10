"""Walk files, dispatch extractors and assemble scan reports."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from pathlib import Path

from metascan import __version__
from metascan.detect import (
    IMAGE_TYPES,
    detect_type,
    is_supported,
    should_skip_dir,
)
from metascan.extractors import empty_report, extract_native
from metascan.extractors.exiftool import extract_exiftool_fields
from metascan.models import Field, FileReport, ScanResult
from metascan.risk import assess_risks

logger = logging.getLogger(__name__)


def collect_paths(targets: Sequence[Path], recursive: bool = False) -> list[Path]:
    """Expand files and directories into a sorted list of file paths."""

    found: list[Path] = []
    missing: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_file():
            found.append(path)
            continue
        if path.is_dir():
            found.extend(_iter_dir(path, recursive=recursive))
            continue
        missing.append(path)
    if missing and not found:
        names = ", ".join(str(item) for item in missing)
        raise FileNotFoundError(f"caminho não encontrado: {names}")
    if missing:
        for item in missing:
            logger.warning("Caminho ignorado (não existe): %s", item)
    return sorted({item.resolve() for item in found})


def _iter_dir(root: Path, recursive: bool) -> list[Path]:
    files: list[Path] = []
    if recursive:
        for current in sorted(root.rglob("*")):
            if current.is_dir() and should_skip_dir(current):
                continue
            if any(should_skip_dir(parent) for parent in current.parents):
                continue
            if current.is_file():
                files.append(current)
        return files
    for current in sorted(root.iterdir()):
        if current.is_file():
            files.append(current)
    return files


def scan_file(path: Path, use_exiftool: bool = True) -> FileReport:
    """Analyze a single file and return a privacy-aware report."""

    path = Path(path)
    if not path.is_file():
        return empty_report(path, "unknown", error=f"arquivo não encontrado: {path}")

    file_type = detect_type(path)
    if file_type == "heic" and not _heic_supported():
        return empty_report(
            path,
            file_type,
            error=(
                "arquivo HEIC/HEIF detectado, mas o extra opcional 'pillow-heif' não está instalado"
            ),
        )
    if not is_supported(file_type):
        return empty_report(
            path,
            file_type,
            error=f"tipo de arquivo não suportado: {file_type}",
        )

    try:
        fields, gps = extract_native(path, file_type)
    except ValueError as exc:
        logger.info("Falha ao extrair metadados de %s: %s", path, exc)
        return empty_report(path, file_type, error=str(exc))
    except OSError as exc:
        logger.info("Erro de I/O em %s: %s", path, exc)
        return empty_report(path, file_type, error=str(exc))

    if use_exiftool:
        extras = extract_exiftool_fields(path)
        fields = _merge_fields(fields, extras)

    risks, level = assess_risks(fields, gps)
    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    return FileReport(
        path=str(path),
        file_type=file_type,
        size_bytes=size,
        fields=fields,
        gps=gps,
        risks=risks,
        risk_level=level,
    )


def scan_paths(
    targets: Sequence[Path],
    recursive: bool = False,
    use_exiftool: bool = True,
) -> ScanResult:
    """Analyze every collected path and return an aggregate result."""

    files = collect_paths(targets, recursive)
    reports = [scan_file(path, use_exiftool=use_exiftool) for path in files]
    return ScanResult(reports=reports, version=__version__)


def _merge_fields(base: list[Field], extras: Iterable[Field]) -> list[Field]:
    known = {item.name.lower() for item in base}
    merged = list(base)
    for item in extras:
        if item.name.lower() in known:
            continue
        known.add(item.name.lower())
        merged.append(item)
    return merged


def _heic_supported() -> bool:
    if "heic" not in IMAGE_TYPES:
        return False
    try:
        import pillow_heif  # noqa: F401
    except ImportError:
        return False
    return True
