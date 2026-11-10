"""End-to-end tests for the metascan command-line interface."""

from __future__ import annotations

import json

from metascan.cli import main


def test_cli_json_output_for_jpeg(jpeg_with_exif, capsys):
    code = main([str(jpeg_with_exif), "--format", "json", "--no-exiftool"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["scanned"] == 1
    assert payload["highest_risk"] == "high"
    assert payload["files"][0]["gps"] is not None


def test_cli_csv_and_markdown(pdf_with_metadata, capsys):
    csv_code = main([str(pdf_with_metadata), "--format", "csv", "--no-exiftool"])
    csv_out = capsys.readouterr().out
    md_code = main([str(pdf_with_metadata), "--format", "markdown", "--no-exiftool"])
    md_out = capsys.readouterr().out

    assert csv_code == 0
    assert md_code == 0
    assert csv_out.splitlines()[0].startswith("path,file_type,size_bytes,risk_level")
    assert "Ana Silva" in csv_out
    assert "# Relatório de metadados" in md_out
    assert "Ana Silva" in md_out


def test_cli_recursive_directory(sample_tree, capsys):
    code = main([str(sample_tree), "--recursive", "--format", "json", "--no-exiftool"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    types = {item["file_type"] for item in payload["files"]}
    assert {"jpeg", "pdf", "docx", "unknown"} <= types


def test_cli_missing_path_returns_2(tmp_path, capsys):
    missing = tmp_path / "nao-existe.jpg"
    code = main([str(missing)])
    err = capsys.readouterr().err

    assert code == 2
    assert "não encontrado" in err


def test_cli_strip_writes_sidecar(jpeg_with_exif, tmp_path, capsys):
    out_dir = tmp_path / "clean"
    code = main(
        [
            str(jpeg_with_exif),
            "--strip",
            "--strip-dir",
            str(out_dir),
            "--format",
            "json",
            "--no-exiftool",
        ]
    )
    err = capsys.readouterr().err
    created = list(out_dir.glob("*_clean.jpg"))

    assert code == 0
    assert created
    assert "Cópia limpa criada" in err


def test_cli_fail_on_risk(jpeg_with_exif, plain_jpeg):
    high = main(
        [str(jpeg_with_exif), "--format", "json", "--fail-on-risk", "high", "--no-exiftool"]
    )
    none = main([str(plain_jpeg), "--format", "json", "--fail-on-risk", "high", "--no-exiftool"])

    assert high == 1
    assert none == 0


def test_cli_output_file(pdf_with_metadata, tmp_path):
    target = tmp_path / "relatorio.json"
    code = main(
        [
            str(pdf_with_metadata),
            "--format",
            "json",
            "--output",
            str(target),
            "--no-exiftool",
        ]
    )

    assert code == 0
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["files"][0]["file_type"] == "pdf"


def test_cli_table_mentions_filename(jpeg_with_exif, capsys):
    code = main([str(jpeg_with_exif), "--format", "table", "--no-exiftool"])
    out = capsys.readouterr().out

    assert code == 0
    assert jpeg_with_exif.name in out
    assert "ALTO" in out or "HIGH" in out
    assert "Google Maps" in out
