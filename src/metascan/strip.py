"""Create cleaned copies of images with EXIF and similar metadata removed.

The original file is never overwritten.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from metascan.detect import IMAGE_TYPES, detect_type

logger = logging.getLogger(__name__)

JPEG_TYPES = frozenset({"jpeg"})


class StripError(RuntimeError):
    """Raised when a cleaned copy cannot be produced."""


def cleaned_destination(
    source: Path,
    suffix: str = "_clean",
    directory: Path | None = None,
) -> Path:
    """Return the destination path for a cleaned copy of ``source``."""

    base = directory if directory is not None else source.parent
    destination = base / f"{source.stem}{suffix}{source.suffix}"
    if destination.resolve() == source.resolve():
        raise StripError("o caminho de destino não pode ser o arquivo original")
    return destination


def strip_image(
    source: Path,
    destination: Path | None = None,
    suffix: str = "_clean",
    directory: Path | None = None,
) -> Path:
    """Write a metadata-stripped copy of ``source`` and return its path."""

    source = Path(source)
    if not source.is_file():
        raise StripError(f"arquivo não encontrado: {source}")

    file_type = detect_type(source)
    if file_type not in IMAGE_TYPES:
        raise StripError(
            f"remoção de metadados disponível apenas para imagens (recebido: {file_type})"
        )

    dest = destination or cleaned_destination(source, suffix=suffix, directory=directory)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if file_type in JPEG_TYPES:
        if _strip_jpeg_lossless(source, dest):
            return dest
        logger.debug("Falling back to Pillow recompression for %s", source)

    _strip_with_pillow(source, dest, file_type)
    return dest


def _strip_jpeg_lossless(source: Path, dest: Path) -> bool:
    try:
        import piexif
    except ImportError:
        return False
    try:
        shutil.copy2(source, dest)
        piexif.remove(str(dest))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("piexif.remove failed for %s: %s", source, exc)
        if dest.exists() and dest.resolve() != source.resolve():
            dest.unlink(missing_ok=True)
        return False


def _strip_with_pillow(source: Path, dest: Path, file_type: str) -> None:
    try:
        with Image.open(source) as image:
            payload = image.copy()
            fmt = image.format or file_type.upper()
            save_kwargs: dict[str, object] = {}
            if fmt.upper() in {"JPEG", "JPG"}:
                save_kwargs["quality"] = 95
                save_kwargs["exif"] = b""
            elif fmt.upper() == "PNG":
                save_kwargs["pnginfo"] = None
            elif fmt.upper() == "WEBP":
                save_kwargs["exif"] = b""
            payload.save(dest, format=fmt, **save_kwargs)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise StripError(f"não foi possível gerar cópia limpa de {source.name}: {exc}") from exc
