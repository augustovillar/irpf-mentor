from __future__ import annotations

from pathlib import Path

import pytest

from irpf_mcp.tools import (
    decode_declaration,
    diff_declarations,
    encode_declaration,
    explain_field,
    list_record_types,
    lookup_pergunta,
    sanity_check,
    tax_summary,
    validate_field,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "fixtures" / "synthetic-2026.dbk"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_decode_declaration_shape() -> None:
    d = decode_declaration(str(FIXTURE))
    assert d["tax_year"] == 2026
    assert d["header"]["nome"] == "REG_HEADER"
    assert d["identificacao"]["nome"] == "REG_IDENTIFICACAO"
    assert len(d["records"]) == 16
    # Header CPF should be the synthetic one
    assert d["header"]["fields"]["NR_CPF"] == "00000000191"
    # Trailer is last
    assert d["records"][-1]["identificador"] == "T9"
    assert d["records"][-1]["nome"] == "REG_TRAILLER"


def test_explain_field_whole_record() -> None:
    out = explain_field("IR")
    assert out["identificador"] == "IR"
    assert out["nome"] == "REG_HEADER"
    assert out["tamanho_total"] == 1244
    # The header has 160 campos including the dup FILLERs
    assert len(out["campos"]) >= 100


def test_explain_field_one_field() -> None:
    out = explain_field("IR", "NR_CPF")
    assert out["record"]["identificador"] == "IR"
    assert out["field"]["nome"] == "NR_CPF"
    assert out["field"]["tamanho"] == 11
    assert "CPF" in out["field"]["descricao"]


def test_explain_field_unknown_field_raises() -> None:
    with pytest.raises(KeyError):
        explain_field("IR", "NOT_A_REAL_FIELD")


def test_list_record_types_returns_all_86() -> None:
    recs = list_record_types()
    assert len(recs) >= 80
    identificadores = {r["identificador"] for r in recs}
    for required in ("IR", "16", "27", "26", "T9"):
        assert required in identificadores


def test_lookup_pergunta_finds_relevant_results() -> None:
    """Searching for a common topic must return on-topic Q&As."""
    results = lookup_pergunta("previdencia privada PGBL", top_k=5)
    assert results, "No results for 'previdencia privada PGBL'"
    assert len(results) <= 5
    # All results should have non-empty resposta
    for r in results:
        assert r["titulo"]
        assert r["resposta"]
        assert r["score"] > 0
    # Strongly expect at least one result to mention PGBL or previdencia
    top = results[0]
    blob = (top["titulo"] + " " + top["resposta"]).lower()
    assert "previd" in blob or "pgbl" in blob


def test_lookup_pergunta_empty_query() -> None:
    assert lookup_pergunta("", top_k=5) == []


def test_lookup_pergunta_top_k_cap() -> None:
    # Common term — should hit many docs, but we cap at top_k
    results = lookup_pergunta("declaração", top_k=3)
    assert len(results) == 3


def test_validate_field_accepts_valid_cpf() -> None:
    out = validate_field("16", "NR_CPF", "00000000191")
    assert out["ok"] is True
    assert out["errors"] == []


def test_validate_field_rejects_overlong_alpha() -> None:
    # NM_NOME in REG_HEADER is A60
    out = validate_field("IR", "NM_NOME", "X" * 61)
    assert out["ok"] is False
    assert any("exceeds maximum" in e for e in out["errors"])


def test_validate_field_rejects_non_numeric() -> None:
    # EXERCICIO is N4 (numeric); letters are invalid.
    out = validate_field("IR", "EXERCICIO", "abc")
    assert out["ok"] is False
    assert out["errors"]


def test_validate_field_rejects_numeric_overflow() -> None:
    # EXERCICIO holds 4 digits; 5 digits overflow the field.
    out = validate_field("IR", "EXERCICIO", "12345")
    assert out["ok"] is False
    assert any("exceeds" in e for e in out["errors"])


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_sanity_check_clean_fixture() -> None:
    """The synthetic fixture has consistent CPFs — no 'error'-level findings."""
    findings = sanity_check(str(FIXTURE))
    errors = [f for f in findings if f["level"] == "error"]
    assert errors == [], f"Unexpected errors: {errors}"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_diff_identical_files_has_no_changes() -> None:
    result = diff_declarations(str(FIXTURE), str(FIXTURE))
    assert result["singleton_changes"] == {}
    assert result["record_set_changes"] == {}


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_diff_detects_name_change(tmp_path) -> None:
    """Changing the name in REG_HEADER should show up as a singleton change."""
    from irpf_core import decode_bytes, encode

    original = FIXTURE.read_bytes()
    decl = decode_bytes(original)
    # Mutate the header name (keep length identical)
    new_name = "MARIA DE SOUZA TESTE".ljust(len(decl.header.fields["NM_NOME"]))
    decl.header.fields["NM_NOME"] = new_name.encode("ascii")
    modified = tmp_path / "modified.dbk"
    modified.write_bytes(encode(decl))

    result = diff_declarations(str(FIXTURE), str(modified))
    assert "REG_HEADER" in result["singleton_changes"]
    assert "NM_NOME" in result["singleton_changes"]["REG_HEADER"]


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_encode_declaration_round_trips(tmp_path) -> None:
    """decode_declaration → encode_declaration must reproduce the file exactly."""
    original = FIXTURE.read_bytes()
    decoded = decode_declaration(str(FIXTURE))
    out = tmp_path / "rebuilt.dbk"
    result = encode_declaration(decoded, str(out))
    assert result["record_count"] == 16
    assert out.read_bytes() == original, "Encode did not reproduce original bytes"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_encode_declaration_applies_edits(tmp_path) -> None:
    """Editing a field's content (same width) is reflected in the output."""
    decoded = decode_declaration(str(FIXTURE))
    # Change UF from SP to RJ in the header (both 2 chars)
    decoded["header"]["fields"]["SG_UF"] = "RJ"
    out = tmp_path / "edited.dbk"
    encode_declaration(decoded, str(out))
    rebuilt = decode_declaration(str(out))
    assert rebuilt["header"]["fields"]["SG_UF"] == "RJ"


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_tax_summary_reads_stored_values() -> None:
    summary = tax_summary(str(FIXTURE))
    assert summary["modelo"] == "simplificada"
    assert summary["disclaimer"]
    assert summary["valores"], "Expected non-empty tax values"
    # The fixture has isentos of R$51,000.00 stored
    campos = {v["campo"] for v in summary["valores"]}
    assert any("ISENTO" in c for c in campos)
    for v in summary["valores"]:
        assert isinstance(v["valor"], float)
