from __future__ import annotations

from pathlib import Path

import pytest

from irpf_core import decode
from irpf_core.informes import FieldMapping, available_sources, parse_informe, register
from irpf_core.informes.base import _PARSERS
from irpf_core.informes.detect import detect_sources

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "fixtures" / "synthetic-2026.dbk"


@pytest.fixture(autouse=True)
def _clean_registry():
    """Each test starts with an empty parser registry."""
    saved = list(_PARSERS)
    _PARSERS.clear()
    yield
    _PARSERS.clear()
    _PARSERS.extend(saved)


class _DummyParser:
    source_kind = "dummy_bank"

    def detect(self, content: str) -> bool:
        return "DUMMY BANK" in content

    def parse(self, content: str) -> list[FieldMapping]:
        return [FieldMapping(
            ficha="Bens e Direitos", record_type="27",
            field_name="VR_ATUAL", value="1234.56", confidence=0.9,
            note="from dummy",
        )]


def test_registry_starts_empty() -> None:
    assert available_sources() == []


def test_register_and_named_dispatch() -> None:
    register(_DummyParser())
    assert available_sources() == ["dummy_bank"]
    mappings = parse_informe("anything", source_kind="dummy_bank")
    assert len(mappings) == 1
    assert mappings[0].record_type == "27"
    assert mappings[0].as_dict()["value"] == "1234.56"


def test_auto_detect_dispatch() -> None:
    register(_DummyParser())
    mappings = parse_informe("statement from DUMMY BANK S.A.")
    assert mappings[0].ficha == "Bens e Direitos"


def test_unknown_source_raises() -> None:
    with pytest.raises(LookupError):
        parse_informe("content", source_kind="nonexistent")


def test_no_parser_matches_raises() -> None:
    register(_DummyParser())
    with pytest.raises(LookupError):
        parse_informe("unrelated content with no signature")


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_detect_sources_finds_institutions() -> None:
    decl = decode(FIXTURE)
    sources = detect_sources(decl)
    # The fixture is fully redacted, so institution names are synthetic — we
    # assert the detector finds the records that cite a third party, not the
    # (now synthetic) names themselves.
    assert sources, "Expected at least one detected source"
    record_kinds = {r["nome_registro"] for s in sources for r in s["records"]}
    assert "REG_PAGAMENTO" in record_kinds  # medical payments
    assert any(k.startswith("REG_RENDIMENTO_EXCLUSIVO") for k in record_kinds)
    for s in sources:
        assert s["records"]
