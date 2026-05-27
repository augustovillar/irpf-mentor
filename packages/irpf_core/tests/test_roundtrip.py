from __future__ import annotations

from pathlib import Path

import pytest

from irpf_core import (
    Declaration,
    TypedRecord,
    decode,
    decode_bytes,
    encode,
    field_int,
    field_str,
)
from irpf_knowledge import record_layout

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "fixtures" / "synthetic-2026.dbk"


def _build_minimal_header() -> TypedRecord:
    """Build a REG_HEADER TypedRecord from scratch using the leiaute.

    Walks every campo in layout order so duplicates (FILLER appears
    multiple times) are disambiguated the same way the parser does.
    """
    layout = record_layout("IR")
    fields: dict[str, bytes] = {}
    for campo in layout["campos"]:
        nome = campo["nome"]
        tamanho = campo["tamanho"]
        if nome == "SISTEMA":
            value = b"IRPF    "
        elif nome == "EXERCICIO":
            value = b"2026"
        elif nome == "ANO_BASE":
            value = b"2025"
        elif nome == "NR_CPF":
            value = b"00000000191"
        elif nome == "NM_NOME":
            value = b"JOAO DA SILVA".ljust(tamanho)
        elif nome == "SG_UF":
            value = b"SP"
        elif nome == "DT_NASCIM":
            value = b"01011990"
        elif campo["tipo"] == "N":
            value = b"0" * tamanho
        else:
            value = b" " * tamanho
        # Disambiguate duplicate names (FILLER appears multiple times)
        key = nome
        if key in fields:
            suffix = 2
            while f"{nome}__{suffix}" in fields:
                suffix += 1
            key = f"{nome}__{suffix}"
        fields[key] = value
    return TypedRecord(identificador="IR", nome="REG_HEADER", fields=fields)


def test_round_trip_minimal_in_memory() -> None:
    header = _build_minimal_header()
    decl = Declaration(records=[header])
    out = encode(decl)
    reparsed = decode_bytes(out)
    assert encode(reparsed) == out


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_fixture_round_trips_byte_for_byte() -> None:
    original = FIXTURE.read_bytes()
    decl = decode_bytes(original)
    assert encode(decl) == original, "Decode → encode produced different bytes"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_every_record_in_fixture_is_typed() -> None:
    """No OpaqueRecord fallbacks should occur — all 16 records in the
    synthetic fixture must be in the leiaute."""
    decl = decode(FIXTURE)
    for r in decl.records:
        assert isinstance(r, TypedRecord), (
            f"Record {r.identificador!r} fell back to OpaqueRecord — its "
            f"identifier isn't in the leiaute."
        )


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_header_field_accessors_work() -> None:
    decl = decode(FIXTURE)
    assert field_str(decl.header, "SISTEMA") == "IRPF"  # rstrip
    assert field_str(decl.header, "EXERCICIO") == "2026"
    assert field_str(decl.header, "ANO_BASE") == "2025"
    assert field_str(decl.header, "NR_CPF") == "00000000191"
    assert field_str(decl.header, "SG_UF") == "SP"
    assert field_str(decl.header, "DT_NASCIM") == "01011990"
    assert field_int(decl.header, "EXERCICIO") == 2026
    assert field_int(decl.header, "ANO_BASE") == 2025


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_identificacao_and_trailer_accessible() -> None:
    decl = decode(FIXTURE)
    assert decl.identificacao.identificador == "16"
    assert decl.identificacao.nome == "REG_IDENTIFICACAO"
    assert decl.trailer.identificador == "T9"
    assert decl.trailer.nome == "REG_TRAILLER"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_synthetic_fixture_is_redacted() -> None:
    """The committed fixture must carry the synthetic CPF, not a real one.

    We assert the positive (synthetic CPF present) rather than hardcoding a
    real CPF to check its absence — hardcoding real PII in the test would
    itself be a leak.
    """
    decl = decode(FIXTURE)
    assert field_str(decl.header, "NR_CPF") == "00000000191"
    assert field_str(decl.identificacao, "NR_CPF") == "00000000191"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_bens_records_present_and_parseable() -> None:
    """The fixture has 2 REG_BEM records (code 27). Each must parse and
    expose its TIPO/DISCRIMINACAO fields."""
    decl = decode(FIXTURE)
    bens = decl.all("27")
    assert len(bens) == 2
    for bem in bens:
        assert bem.nome == "REG_BEM"
        # CD_BEM is the asset type code, TX_BEM is the free-text description
        assert "CD_BEM" in bem.fields
        assert "TX_BEM" in bem.fields
        # Both bens in the fixture are real assets (titulos publicos / RDB)
        assert field_str(bem, "TX_BEM"), "TX_BEM unexpectedly empty"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_pagamento_records_present_and_parseable() -> None:
    """The fixture has 3 REG_PAGAMENTO records (code 26)."""
    decl = decode(FIXTURE)
    pagamentos = decl.all("26")
    assert len(pagamentos) == 3
    for pag in pagamentos:
        assert pag.nome == "REG_PAGAMENTO"
