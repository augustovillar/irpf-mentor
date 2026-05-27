from __future__ import annotations

from pathlib import Path

import pytest

from irpf_knowledge import load_ajuda, load_leiaute, load_perguntas, record_layout

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "fixtures" / "synthetic-2026.dbk"


def test_leiaute_loads() -> None:
    le = load_leiaute(2026)
    assert le["tax_year"] == 2026
    assert le["ano_base"] == 2025
    assert le["tipo_arquivo"] == "ARQ_IRPF"
    assert len(le["records"]) >= 80, "Expected at least 80 record types in leiaute"


def test_known_record_codes_present() -> None:
    """Every record type observed in a real declaration must be in the leiaute."""
    for code, expected_nome in [
        ("IR", "REG_HEADER"),
        ("16", "REG_IDENTIFICACAO"),
        ("17", "REG_SIMPLES"),
        ("18", "REG_RESUMOSIMPLES"),
        ("23", "REG_RENDISENTOS"),
        ("24", "REG_RENDEXCLUSIVA"),
        ("26", "REG_PAGAMENTO"),
        ("27", "REG_BEM"),
        ("T9", "REG_TRAILLER"),
    ]:
        layout = record_layout(code)
        assert layout["nome"] == expected_nome, (
            f"Record {code} expected nome={expected_nome}, got {layout['nome']}"
        )


def test_field_offsets_are_sequential() -> None:
    """For every record, sum(tamanho) == tamanho_total and offsets are sequential."""
    le = load_leiaute(2026)
    for code, rec in le["records"].items():
        offset = 0
        for campo in rec["campos"]:
            assert campo["offset"] == offset, (
                f"Record {code} field {campo['nome']}: offset {campo['offset']} "
                f"!= expected {offset}"
            )
            offset += campo["tamanho"]
        assert offset == rec["tamanho_total"], (
            f"Record {code}: sum(tamanho) {offset} != tamanho_total "
            f"{rec['tamanho_total']}"
        )


def test_perguntas_loads() -> None:
    perg = load_perguntas(2026)
    assert len(perg) >= 700, f"Expected ~734 Q&A entries, got {len(perg)}"
    nums = {p["num"] for p in perg}
    assert 1 in nums, "Pergunta 001 missing"
    assert max(nums) >= 740, f"Highest pergunta num is {max(nums)}, expected ~745"
    for p in perg[:5]:
        assert isinstance(p["titulo"], str) and p["titulo"]
        assert isinstance(p["resposta"], str) and p["resposta"]


def test_ajuda_loads_and_has_expected_sections() -> None:
    """AjudaIRPF.md must be present and contain known section headings."""
    md = load_ajuda(2026)
    assert len(md) > 100_000, "AjudaIRPF.md unexpectedly small"
    for required in ("Identificação do Contribuinte", "Dependentes",
                     "Bens e Direitos", "Pagamentos Efetuados"):
        assert required in md, f"AjudaIRPF.md missing section: {required!r}"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_fixture_record_lengths_match_leiaute() -> None:
    """Every record in the synthetic fixture must match its declared tamanho_total."""
    data = FIXTURE.read_bytes()
    records = [r for r in data.split(b"\r\n") if r]
    for rec in records:
        if rec.startswith(b"IRPF"):
            key = "IR"
        else:
            key = rec[:2].decode("ascii")
        layout = record_layout(key)
        assert len(rec) == layout["tamanho_total"], (
            f"Record {key} ({layout['nome']}): actual {len(rec)} bytes, "
            f"declared {layout['tamanho_total']}"
        )
