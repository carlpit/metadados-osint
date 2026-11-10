"""Unit tests for the privacy-risk classifier."""

from __future__ import annotations

from metascan.models import Field, RiskLevel, build_gps
from metascan.risk import assess_risks


def test_gps_and_serial_produce_high_risk():
    fields = [Field(name="BodySerialNumber", value="SN1", category="serial")]
    gps = build_gps(-7.1195, -34.845)
    risks, level = assess_risks(fields, gps)
    codes = {item.code for item in risks}

    assert level is RiskLevel.HIGH
    assert "GPS_COORDINATES" in codes
    assert "DEVICE_SERIAL" in codes


def test_author_without_gps_is_medium():
    fields = [Field(name="Author", value="Ana Silva", category="identity")]
    risks, level = assess_risks(fields, None)

    assert level is RiskLevel.MEDIUM
    assert risks[0].code == "AUTHOR_NAME"


def test_software_only_is_low():
    fields = [Field(name="Software", value="GIMP 2.10", category="software")]
    _, level = assess_risks(fields, None)

    assert level is RiskLevel.LOW


def test_empty_metadata_is_none():
    risks, level = assess_risks([], None)

    assert risks == []
    assert level is RiskLevel.NONE


def test_duplicate_identity_fields_are_not_repeated():
    fields = [
        Field(name="Author", value="Ana", category="identity"),
        Field(name="Author", value="Ana", category="identity"),
    ]
    risks, _ = assess_risks(fields, None)

    assert len([item for item in risks if item.code == "AUTHOR_NAME"]) == 1
