from __future__ import annotations

from pathlib import Path
from typing import Any

from irpf_knowledge import load_leiaute

from .schema import Declaration, OpaqueRecord, TypedRecord

HEADER_PREFIX = b"IRPF"
"""The file header record begins with 'IRPF' (a 4-byte SISTEMA field
spelled "IRPF    "), whereas every other record begins with a 2-char
numeric identifier (16, 27, T9, etc.)."""


def decode(source: str | Path | bytes, tax_year: int = 2026) -> Declaration:
    """Parse a .DBK / .DEC file (or its bytes) into a Declaration.

    Each record is parsed against the leiaute for `tax_year`. Records whose
    identifier isn't in the leiaute become `OpaqueRecord` (raw bytes kept
    for round-trip fidelity).
    """
    if isinstance(source, (str, Path)):
        data = Path(source).read_bytes()
    else:
        data = bytes(source)
    return decode_bytes(data, tax_year=tax_year)


def decode_bytes(data: bytes, tax_year: int = 2026) -> Declaration:
    leiaute = load_leiaute(tax_year)["records"]
    raw_records = data.split(b"\r\n")
    if raw_records and raw_records[-1] == b"":
        raw_records = raw_records[:-1]
    if not raw_records:
        raise ValueError("Empty declaration file (no records)")

    records: list[TypedRecord | OpaqueRecord] = []
    for rec in raw_records:
        identificador = _identify(rec)
        layout = leiaute.get(identificador)
        if layout is None:
            records.append(OpaqueRecord(identificador=identificador, raw=rec))
            continue
        records.append(_parse_typed_record(rec, identificador, layout))

    return Declaration(records=records)


def _identify(rec: bytes) -> str:
    if rec.startswith(HEADER_PREFIX):
        return "IR"
    if len(rec) < 2:
        raise ValueError(f"Record too short to identify: {rec!r}")
    return rec[:2].decode("ascii")


def _parse_typed_record(rec: bytes, identificador: str, layout: dict[str, Any]) -> TypedRecord:
    expected = layout["tamanho_total"]
    if len(rec) != expected:
        raise ValueError(
            f"Record {identificador} ({layout['nome']}): got {len(rec)} bytes, "
            f"leiaute says {expected}"
        )

    fields: dict[str, bytes] = {}
    offset = 0
    for campo in layout["campos"]:
        tamanho = campo["tamanho"]
        end = offset + tamanho
        _add_field(fields, campo["nome"], rec[offset:end])
        offset = end

    return TypedRecord(
        identificador=identificador,
        nome=layout["nome"],
        fields=fields,
    )


def _add_field(fields: dict[str, bytes], name: str, value: bytes) -> None:
    """Insert a field, disambiguating duplicates with __2, __3, … suffixes.

    Several record types (REG_HEADER, REG_BEM, …) have multiple `FILLER`
    fields used as positional padding. We keep them all so encode is bit
    perfect; semantic accessors look up the unsuffixed name (which is the
    one the user cares about).
    """
    if name not in fields:
        fields[name] = value
        return
    suffix = 2
    while f"{name}__{suffix}" in fields:
        suffix += 1
    fields[f"{name}__{suffix}"] = value
