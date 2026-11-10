"""metascan: metadata analyzer for images and office documents."""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Carlos Vinicius"

from metascan.models import FileReport, GPSData, RiskLevel, ScanResult

__all__ = [
    "__version__",
    "FileReport",
    "GPSData",
    "RiskLevel",
    "ScanResult",
]
