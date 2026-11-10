"""Command-line interface for metascan."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from metascan import __version__
from metascan.detect import IMAGE_TYPES, detect_type
from metascan.formatters import render
from metascan.models import RISK_RANK, RiskLevel, ScanResult
from metascan.scanner import scan_paths
from metascan.strip import StripError, strip_image

logger = logging.getLogger("metascan")


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the ``metascan`` command."""

    parser = argparse.ArgumentParser(
        prog="metascan",
        description=(
            "Analisa metadados de imagens e documentos para OSINT ético "
            "e para revisar o que um arquivo pode vazar antes de ser publicado."
        ),
        epilog=(
            "Use apenas em arquivos seus ou com autorização expressa. "
            "Metadados podem conter dados pessoais protegidos pela LGPD."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Arquivos ou diretórios a analisar",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Percorre diretórios recursivamente",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("table", "json", "csv", "markdown"),
        default="table",
        help="Formato de saída (padrão: table)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Salva o relatório neste arquivo em vez de imprimir no terminal",
    )
    parser.add_argument(
        "--strip",
        action="store_true",
        help="Cria uma cópia das imagens sem EXIF; o original não é alterado",
    )
    parser.add_argument(
        "--strip-suffix",
        default="_clean",
        help="Sufixo da cópia limpa (padrão: _clean)",
    )
    parser.add_argument(
        "--strip-dir",
        type=Path,
        help="Diretório de destino das cópias limpas",
    )
    parser.add_argument(
        "--exiftool",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Usa o binário exiftool se ele estiver instalado (padrão: sim)",
    )
    parser.add_argument(
        "--fail-on-risk",
        choices=("none", "low", "medium", "high"),
        default="none",
        help="Encerra com código 1 se o risco atingir este nível (útil em CI)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Registra detalhes de extração em stderr",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suprime avisos; mostra apenas o relatório",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point used by the console script and by ``python -m metascan``."""

    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        result = scan_paths(
            args.paths,
            recursive=args.recursive,
            use_exiftool=args.exiftool,
        )
    except FileNotFoundError as exc:
        _emit_error(str(exc))
        return 2
    except OSError as exc:
        _emit_error(str(exc))
        return 2

    if args.strip:
        _run_strip(result, suffix=args.strip_suffix, directory=args.strip_dir)

    try:
        payload = render(result, args.format)
    except ValueError as exc:
        _emit_error(str(exc))
        return 2

    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        except OSError as exc:
            _emit_error(f"não foi possível escrever {args.output}: {exc}")
            return 2
        if not args.quiet:
            print(f"Relatório salvo em {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)
        if payload and not payload.endswith("\n"):
            sys.stdout.write("\n")

    return _exit_code(result, args.fail_on_risk)


def _run_strip(result: ScanResult, suffix: str, directory: Path | None) -> None:
    for report in result.reports:
        path = Path(report.path)
        try:
            kind = detect_type(path)
        except OSError:
            continue
        if kind not in IMAGE_TYPES:
            logger.info("Ignorando --strip em %s (não é imagem)", path.name)
            continue
        try:
            dest = strip_image(path, suffix=suffix, directory=directory)
        except StripError as exc:
            logger.warning("Falha ao limpar %s: %s", path.name, exc)
            continue
        logger.info("Cópia sem metadados: %s", dest)
        print(f"Cópia limpa criada: {dest}", file=sys.stderr)


def _exit_code(result: ScanResult, threshold: str) -> int:
    if threshold == "none":
        return 0
    target = RiskLevel(threshold)
    if RISK_RANK[result.highest_risk] >= RISK_RANK[target]:
        return 1
    return 0


def _configure_logging(verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format="metascan: %(levelname)s: %(message)s")


def _emit_error(message: str) -> None:
    print(f"metascan: erro: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
