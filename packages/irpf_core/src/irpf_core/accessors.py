"""Typed read accessors on top of TypedRecord.

Records store field values as raw byte slices (length-preserving for
round-trip). These helpers decode them into Python types per the leiaute's
`tipo` field:

    C  → string (numeric-text content, trailing spaces stripped)
    A  → string (alpha, trailing spaces stripped)
    N  → int (or Decimal if Decimais > 0)
    D  → str in DDMMYYYY format (date class is the user's call)
    I  → bool (true for '1' / 'S', false for '0' / 'N' / ' ')

The accessors take a `TypedRecord` and a field name. The leiaute is loaded
lazily so we know which type each field is.
"""

from __future__ import annotations

from decimal import Decimal
from functools import cache
from typing import Any

from irpf_knowledge import load_leiaute

from .schema import TypedRecord


@cache
def _field_lookup(tax_year: int = 2026) -> dict[tuple[str, str], dict[str, Any]]:
    """Build a (identificador, field_name) → campo-spec map for fast lookup."""
    leiaute = load_leiaute(tax_year)["records"]
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for identificador, layout in leiaute.items():
        for campo in layout["campos"]:
            out[(identificador, campo["nome"])] = campo
    return out


def field_spec(record: TypedRecord, name: str, tax_year: int = 2026) -> dict[str, Any]:
    """Return the leiaute spec dict for one field of a record."""
    try:
        return _field_lookup(tax_year)[(record.identificador, name)]
    except KeyError:
        raise KeyError(
            f"Field {name!r} not in leiaute for record {record.identificador} "
            f"({record.nome})"
        ) from None


def field_str(record: TypedRecord, name: str) -> str:
    """Decode an Alpha/Char field, stripping trailing spaces.

    For Numeric fields, returns the digits as a string (leading zeros kept).
    """
    return record.fields[name].decode("ascii").rstrip(" ")


def field_int(record: TypedRecord, name: str) -> int:
    """Decode a Numeric field with no decimals (or `Decimais=0`)."""
    raw = record.fields[name].decode("ascii").strip() or "0"
    return int(raw)


def field_decimal(record: TypedRecord, name: str,
                  tax_year: int = 2026) -> Decimal:
    """Decode a Numeric field with implied decimals (from the leiaute).

    The on-disk value is the unsigned integer; we scale it by 10^-decimals
    based on the leiaute's `decimais` attribute. E.g. `0000000010000` with
    `decimais=2` returns `Decimal("100.00")`.
    """
    spec = field_spec(record, name, tax_year)
    decimals = int(spec.get("decimais", 0))
    raw = record.fields[name].decode("ascii").strip() or "0"
    if decimals == 0:
        return Decimal(raw)
    return Decimal(raw) / (Decimal(10) ** decimals)


def field_date(record: TypedRecord, name: str) -> str:
    """Return a Date field's raw DDMMYYYY string (no parsing — let caller decide).

    Returns an empty string if the field is all-zero/blank.
    """
    raw = record.fields[name].decode("ascii").strip()
    if not raw or raw == "0" * len(raw):
        return ""
    return raw


def field_bool(record: TypedRecord, name: str) -> bool:
    """Decode an Indicator field. True iff the byte is '1' or 'S'."""
    raw = record.fields[name].decode("ascii").strip()
    return raw in ("1", "S", "s")
