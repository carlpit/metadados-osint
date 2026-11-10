"""Privacy-risk classification for extracted metadata."""

from __future__ import annotations

from metascan.models import Field, GPSData, Risk, RiskLevel, max_risk

# Categories assigned by extractors.
IDENTITY_CATEGORIES = {"identity"}
SERIAL_CATEGORIES = {"serial"}
SOFTWARE_CATEGORIES = {"software"}
DEVICE_CATEGORIES = {"device"}
SYSTEM_CATEGORIES = {"system"}

_MESSAGES = {
    "GPS_COORDINATES": (
        "coordenadas de geolocalização presentes; podem revelar onde o arquivo foi criado"
    ),
    "DEVICE_SERIAL": "número de série de dispositivo encontrado",
    "AUTHOR_NAME": "nome de autor, artista ou usuário encontrado",
    "HOST_COMPUTER": "nome de computador ou host encontrado",
    "SOFTWARE_VERSION": "software ou versão identificável (pode auxiliar em fingerprinting)",
    "DEVICE_MODEL": "fabricante ou modelo de dispositivo identificável",
}


def assess_risks(fields: list[Field], gps: GPSData | None) -> tuple[list[Risk], RiskLevel]:
    """Return privacy findings and the overall risk level for a file."""

    findings: list[Risk] = []

    if gps is not None:
        findings.append(
            Risk(
                code="GPS_COORDINATES",
                level=RiskLevel.HIGH,
                message=_MESSAGES["GPS_COORDINATES"],
                field="GPS",
                value=f"{gps.latitude},{gps.longitude}",
            )
        )

    seen_codes: set[tuple[str, str]] = set()
    for item in fields:
        risk = _risk_for_field(item)
        if risk is None:
            continue
        key = (risk.code, risk.value.casefold())
        if key in seen_codes:
            continue
        seen_codes.add(key)
        findings.append(risk)

    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda item: (order[item.level.value], item.code))
    level = max_risk([item.level for item in findings])
    return findings, level


def _risk_for_field(item: Field) -> Risk | None:
    if item.category in SERIAL_CATEGORIES:
        return Risk(
            code="DEVICE_SERIAL",
            level=RiskLevel.HIGH,
            message=_MESSAGES["DEVICE_SERIAL"],
            field=item.name,
            value=item.value,
        )
    if item.category in IDENTITY_CATEGORIES:
        return Risk(
            code="AUTHOR_NAME",
            level=RiskLevel.MEDIUM,
            message=_MESSAGES["AUTHOR_NAME"],
            field=item.name,
            value=item.value,
        )
    if item.category in SYSTEM_CATEGORIES:
        return Risk(
            code="HOST_COMPUTER",
            level=RiskLevel.MEDIUM,
            message=_MESSAGES["HOST_COMPUTER"],
            field=item.name,
            value=item.value,
        )
    if item.category in SOFTWARE_CATEGORIES:
        return Risk(
            code="SOFTWARE_VERSION",
            level=RiskLevel.LOW,
            message=_MESSAGES["SOFTWARE_VERSION"],
            field=item.name,
            value=item.value,
        )
    if item.category in DEVICE_CATEGORIES:
        return Risk(
            code="DEVICE_MODEL",
            level=RiskLevel.LOW,
            message=_MESSAGES["DEVICE_MODEL"],
            field=item.name,
            value=item.value,
        )
    return None
