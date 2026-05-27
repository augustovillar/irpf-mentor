"""Field-level validation derived from the leiaute and CampoTXT semantics.

The official SERPRO CampoTXT class enforces, per field type:
    N (numeric): digits only (Long/Double-parseable); length ≤ tamanho;
                 if decimais > 0, the dot-form must not exceed those decimals.
    A (alpha) / C (char): length ≤ tamanho.
    D (date): DDMMAAAA, length ≤ 8.
    I (indicator): a single 'S'/'N'/'0'/'1'/' '.

`validate_value` re-implements those checks against the leiaute spec so the
MCP can tell a user whether a value they intend to write is acceptable
before it ever touches the official program.
"""

from __future__ import annotations

import re

from irpf_knowledge import record_layout

_DIGITS = re.compile(r"^\d+$")
_DATE = re.compile(r"^\d{8}$")


def validate_value(record_type: str, field_name: str, value: str) -> list[str]:
    """Return a list of human-readable errors; empty list means valid.

    `value` is the *logical* value the user wants to store (not the padded
    on-disk form). For numerics, pass digits (optionally with a decimal
    point); for alpha, pass the text without padding.
    """
    spec = _field_spec(record_type, field_name)
    tipo = spec["tipo"]
    tamanho = spec["tamanho"]
    decimais = int(spec.get("decimais", 0))
    errors: list[str] = []

    if tipo in ("A", "C"):
        if len(value) > tamanho:
            errors.append(
                f"{field_name}: length {len(value)} exceeds maximum {tamanho}"
            )
    elif tipo == "N":
        digits = value.replace(".", "").replace(",", "").lstrip("-")
        if not digits:
            errors.append(f"{field_name}: numeric value is empty")
        elif not _DIGITS.match(digits):
            errors.append(f"{field_name}: not a valid number: {value!r}")
        else:
            if decimais > 0 and ("." in value or "," in value):
                frac = re.split(r"[.,]", value, maxsplit=1)[1]
                if len(frac) > decimais:
                    errors.append(
                        f"{field_name}: {len(frac)} decimal places exceeds "
                        f"the {decimais} allowed"
                    )
            integer_capacity = tamanho - decimais
            int_part = re.split(r"[.,]", value, maxsplit=1)[0].lstrip("-")
            if len(int_part) > integer_capacity:
                errors.append(
                    f"{field_name}: integer part {int_part!r} exceeds "
                    f"{integer_capacity} digits (field holds {tamanho} digits "
                    f"with {decimais} decimal places)"
                )
    elif tipo == "D":
        if value and not _DATE.match(value):
            errors.append(f"{field_name}: date must be DDMMAAAA (8 digits), got {value!r}")
    elif tipo == "I":
        if value not in ("S", "N", "0", "1", " ", ""):
            errors.append(f"{field_name}: indicator must be S/N/0/1, got {value!r}")
    else:
        errors.append(f"{field_name}: unknown field type {tipo!r} in leiaute")

    return errors


def _field_spec(record_type: str, field_name: str) -> dict:
    layout = record_layout(record_type)
    for campo in layout["campos"]:
        if campo["nome"] == field_name:
            return campo
    raise KeyError(
        f"Field {field_name!r} not found in record {record_type} ({layout['nome']})"
    )
