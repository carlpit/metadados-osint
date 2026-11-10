"""Data models for metadata scan results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    """Overall privacy risk associated with a file's metadata."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


RISK_RANK: dict[RiskLevel, int] = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
}


def max_risk(levels: list[RiskLevel]) -> RiskLevel:
    """Return the highest risk level from ``levels``."""

    if not levels:
        return RiskLevel.NONE
    return max(levels, key=lambda level: RISK_RANK[level])


@dataclass(frozen=True)
class GPSData:
    """Decimal GPS coordinates plus shareable map URLs (no network I/O)."""

    latitude: float
    longitude: float
    google_maps: str
    openstreetmap: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize coordinates and map links."""

        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "google_maps": self.google_maps,
            "openstreetmap": self.openstreetmap,
        }


def build_gps(latitude: float, longitude: float) -> GPSData:
    """Build a ``GPSData`` value with 6-decimal precision and map URLs."""

    lat = round(float(latitude), 6)
    lon = round(float(longitude), 6)
    return GPSData(
        latitude=lat,
        longitude=lon,
        google_maps=f"https://www.google.com/maps?q={lat},{lon}",
        openstreetmap=(f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"),
    )


@dataclass(frozen=True)
class Field:
    """A single extracted metadata field."""

    name: str
    value: str
    category: str
    raw_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the field."""

        payload: dict[str, Any] = {
            "name": self.name,
            "value": self.value,
            "category": self.category,
        }
        if self.raw_key:
            payload["raw_key"] = self.raw_key
        return payload


@dataclass(frozen=True)
class Risk:
    """A privacy finding derived from one or more metadata fields."""

    code: str
    level: RiskLevel
    message: str
    field: str
    value: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the finding."""

        return {
            "code": self.code,
            "level": self.level.value,
            "message": self.message,
            "field": self.field,
            "value": self.value,
        }


@dataclass
class FileReport:
    """Complete analysis of a single file."""

    path: str
    file_type: str
    size_bytes: int
    fields: list[Field] = field(default_factory=list)
    gps: GPSData | None = None
    risks: list[Risk] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.NONE
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report, including nested GPS and risks."""

        return {
            "path": self.path,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "risk_level": self.risk_level.value,
            "gps": self.gps.to_dict() if self.gps else None,
            "fields": [item.to_dict() for item in self.fields],
            "risks": [item.to_dict() for item in self.risks],
            "error": self.error,
        }


@dataclass
class ScanResult:
    """Aggregate result for one or more files."""

    reports: list[FileReport]
    version: str

    @property
    def scanned(self) -> int:
        """Number of files visited."""

        return len(self.reports)

    @property
    def errors(self) -> int:
        """Number of files that produced an extraction error."""

        return sum(1 for report in self.reports if report.error)

    @property
    def highest_risk(self) -> RiskLevel:
        """Highest privacy risk across all reports."""

        return max_risk([report.risk_level for report in self.reports])

    def to_dict(self) -> dict[str, Any]:
        """Serialize the aggregate result."""

        return {
            "version": self.version,
            "scanned": self.scanned,
            "errors": self.errors,
            "highest_risk": self.highest_risk.value,
            "files": [report.to_dict() for report in self.reports],
        }
