"""Render scan results as a table, JSON, CSV or Markdown report."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from pathlib import Path

from metascan.models import Field, FileReport, RiskLevel, ScanResult

RISK_LABELS = {
    RiskLevel.NONE: "NENHUM",
    RiskLevel.LOW: "BAIXO",
    RiskLevel.MEDIUM: "MÉDIO",
    RiskLevel.HIGH: "ALTO",
}


def render(result: ScanResult, fmt: str) -> str:
    """Render ``result`` in ``fmt`` (table, json, csv or markdown)."""

    normalized = fmt.lower()
    if normalized == "json":
        return render_json(result)
    if normalized == "csv":
        return render_csv(result)
    if normalized == "markdown":
        return render_markdown(result)
    if normalized == "table":
        return render_table(result)
    raise ValueError(f"formato de saída não suportado: {fmt}")


def render_json(result: ScanResult) -> str:
    """Pretty-printed JSON document."""

    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"


def render_csv(result: ScanResult) -> str:
    """One row per metadata field (plus GPS/risk summary columns)."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "path",
            "file_type",
            "size_bytes",
            "risk_level",
            "category",
            "field",
            "value",
            "gps_latitude",
            "gps_longitude",
            "google_maps",
            "openstreetmap",
            "risks",
            "error",
        ]
    )
    for report in result.reports:
        lat = report.gps.latitude if report.gps else ""
        lon = report.gps.longitude if report.gps else ""
        gmaps = report.gps.google_maps if report.gps else ""
        osm = report.gps.openstreetmap if report.gps else ""
        risks = "; ".join(f"{item.code}:{item.level.value}" for item in report.risks)
        rows = report.fields or [Field(name="", value="", category="")]
        for item in rows:
            writer.writerow(
                [
                    report.path,
                    report.file_type,
                    report.size_bytes,
                    report.risk_level.value,
                    item.category,
                    item.name,
                    item.value,
                    lat,
                    lon,
                    gmaps,
                    osm,
                    risks,
                    report.error or "",
                ]
            )
    return buffer.getvalue()


def render_markdown(result: ScanResult) -> str:
    """Human-readable Markdown report."""

    lines = [
        "# Relatório de metadados",
        "",
        f"Gerado por **metascan** {result.version}.",
        "",
        f"- Arquivos analisados: **{result.scanned}**",
        f"- Falhas de leitura: **{result.errors}**",
        f"- Risco mais alto: **{RISK_LABELS[result.highest_risk]}**",
        "",
    ]
    if not result.reports:
        lines.append("_Nenhum arquivo analisado._")
        lines.append("")
        return "\n".join(lines)

    for report in result.reports:
        lines.extend(_markdown_file(report))
    return "\n".join(lines).rstrip() + "\n"


def _markdown_file(report: FileReport) -> list[str]:
    title = display_name(report.path)
    lines = [
        f"## `{title}`",
        "",
        (
            f"**Tipo:** {report.file_type} · **Tamanho:** {report.size_bytes} bytes"
            f" · **Risco:** {RISK_LABELS[report.risk_level]}"
        ),
        "",
    ]
    if report.error:
        lines.extend([f"> Erro: {report.error}", ""])
        return lines
    if report.gps:
        gps = report.gps
        lines.extend(
            [
                "### GPS",
                "",
                f"- Coordenadas: `{gps.latitude}, {gps.longitude}`",
                f"- [Google Maps]({gps.google_maps}) · [OpenStreetMap]({gps.openstreetmap})",
                "",
            ]
        )
    if report.fields:
        lines.extend(
            [
                "### Campos",
                "",
                "| Categoria | Campo | Valor |",
                "| --- | --- | --- |",
            ]
        )
        for item in report.fields:
            lines.append(f"| {item.category} | {item.name} | {_md_escape(item.value)} |")
        lines.append("")
    if report.risks:
        lines.extend(["### Alertas de privacidade", ""])
        for item in report.risks:
            extra = f" (`{item.value}`)" if item.value else ""
            lines.append(f"- **{RISK_LABELS[item.level]}** `{item.code}` — {item.message}{extra}")
        lines.append("")
    else:
        lines.extend(["_Nenhum alerta de privacidade._", ""])
    return lines


def render_table(result: ScanResult) -> str:
    """Terminal table. Uses Rich when available, otherwise plain text."""

    try:
        return _render_table_rich(result)
    except ImportError:
        return _render_table_plain(result)


def _render_table_plain(result: ScanResult) -> str:
    chunks = [
        f"metascan {result.version}  |  arquivos: {result.scanned}  |"
        f"  falhas: {result.errors}  |  risco mais alto: {RISK_LABELS[result.highest_risk]}",
        "",
    ]
    if not result.reports:
        chunks.append("Nenhum arquivo analisado.")
        chunks.append("")
        return "\n".join(chunks)

    for report in result.reports:
        chunks.extend(_plain_file(report))
    return "\n".join(chunks).rstrip() + "\n"


def _plain_file(report: FileReport) -> list[str]:
    bar = "=" * 78
    dash = "-" * 78
    header = f"{display_name(report.path)}  [{RISK_LABELS[report.risk_level]}]"
    lines = [bar, header, dash]
    lines.append(_kv("Tipo", report.file_type))
    lines.append(_kv("Tamanho", f"{report.size_bytes} bytes"))
    if report.error:
        lines.append(_kv("Erro", report.error))
        lines.append("")
        return lines
    if report.gps:
        lines.append(_kv("GPS", f"{report.gps.latitude}, {report.gps.longitude}"))
        lines.append(_kv("Google Maps", report.gps.google_maps))
        lines.append(_kv("OpenStreetMap", report.gps.openstreetmap))
    for item in report.fields:
        lines.append(_kv(item.name, item.value))
    if report.risks:
        lines.append(dash)
        lines.append("Alertas de privacidade:")
        for item in report.risks:
            extra = f" ({item.value})" if item.value else ""
            lines.append(f"  - [{RISK_LABELS[item.level]}] {item.code}: {item.message}{extra}")
    lines.append("")
    return lines


def _kv(key: str, value: str) -> str:
    return f"  {key:<22} {value}"


def _render_table_rich(result: ScanResult) -> str:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=True, color_system=None, width=100)
    summary = (
        f"metascan {result.version}  •  arquivos: {result.scanned}  •  "
        f"falhas: {result.errors}  •  risco mais alto: {RISK_LABELS[result.highest_risk]}"
    )
    console.print(summary)
    console.print()

    if not result.reports:
        console.print("Nenhum arquivo analisado.")
        return buffer.getvalue()

    colors = {
        RiskLevel.NONE: "green",
        RiskLevel.LOW: "yellow",
        RiskLevel.MEDIUM: "dark_orange",
        RiskLevel.HIGH: "red",
    }
    for report in result.reports:
        risk_text = Text(RISK_LABELS[report.risk_level], style=colors[report.risk_level])
        title = Text(f"{display_name(report.path)}  [")
        title.append(risk_text)
        title.append("]")

        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Campo", style="cyan", no_wrap=True)
        table.add_column("Valor", overflow="fold")
        table.add_row("Tipo", report.file_type)
        table.add_row("Tamanho", f"{report.size_bytes} bytes")
        if report.error:
            table.add_row("Erro", report.error)
        if report.gps:
            table.add_row("GPS", f"{report.gps.latitude}, {report.gps.longitude}")
            table.add_row("Google Maps", report.gps.google_maps)
            table.add_row("OpenStreetMap", report.gps.openstreetmap)
        for item in report.fields:
            table.add_row(item.name, item.value)
        if report.risks:
            table.add_section()
            for item in report.risks:
                extra = f" ({item.value})" if item.value else ""
                table.add_row(
                    f"[{RISK_LABELS[item.level]}] {item.code}",
                    f"{item.message}{extra}",
                )
        console.print(Panel(table, title=title, border_style=colors[report.risk_level]))
        console.print()
    return buffer.getvalue()


def display_name(path: str) -> str:
    """Return the file name portion for headings."""

    return Path(path).name


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def iter_reports(result: ScanResult) -> Iterable[FileReport]:
    """Yield reports (helper for tests and callers)."""

    yield from result.reports
