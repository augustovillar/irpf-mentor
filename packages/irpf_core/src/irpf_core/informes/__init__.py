"""Pluggable framework for mapping source documents (informes) to IRPF fields.

An *informe* is a document a taxpayer receives — an Informe de Rendimentos
Financeiros from a bank, an informe from a corretora, an employer's informe de
rendimentos, etc. Each has a vendor-specific layout. This package provides a
small registry so a parser for one source can be added in isolation:

    from irpf_core.informes import FieldMapping, register

    class MyBankParser:
        source_kind = "mybank_informe_rendimentos"
        def detect(self, content: str) -> bool:
            return "MY BANK S.A." in content
        def parse(self, content: str) -> list[FieldMapping]:
            ...
            return [FieldMapping(ficha="Bens e Direitos", record_type="27",
                                 field_name="VR_ATUAL", value="...", confidence=0.9)]

    register(MyBankParser())

`parse_informe(content)` then auto-routes to the first parser whose `detect`
returns True (or a named parser via `source_kind`).

No concrete source parsers ship yet — each needs a real sample informe to
build and test against. See docs/supported_sources_2026.md for the sources
detected in the reference declaration.
"""

from __future__ import annotations

from .base import (
    FieldMapping,
    InformeParser,
    available_sources,
    parse_informe,
    register,
)

__all__ = [
    "FieldMapping",
    "InformeParser",
    "available_sources",
    "parse_informe",
    "register",
]
