from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class FieldMapping:
    """One suggested declaration edit derived from an informe.

    ficha:        human-readable form name (e.g. "Bens e Direitos").
    record_type:  leiaute identifier the value belongs in (e.g. "27").
    field_name:   field within that record (e.g. "VR_ATUAL").
    value:        logical value (not on-disk-padded). For 2-decimal money
                  fields, give reais as a string like "4528.65".
    confidence:   0..1 — how sure the parser is about this mapping.
    note:         optional human explanation / caveat.
    """

    ficha: str
    record_type: str
    field_name: str
    value: str
    confidence: float = 1.0
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "ficha": self.ficha,
            "record_type": self.record_type,
            "field_name": self.field_name,
            "value": self.value,
            "confidence": self.confidence,
            "note": self.note,
        }


@runtime_checkable
class InformeParser(Protocol):
    """A parser for one informe source.

    Implementations set `source_kind` to a stable slug and implement
    `detect` (cheap content sniff) and `parse` (extract FieldMappings).
    """

    source_kind: str

    def detect(self, content: str) -> bool: ...

    def parse(self, content: str) -> list[FieldMapping]: ...


_PARSERS: list[InformeParser] = []


def register(parser: InformeParser) -> None:
    """Register an informe parser. Later registrations take precedence in
    auto-detection (most-specific parsers can be added last)."""
    _PARSERS.append(parser)


def available_sources() -> list[str]:
    """Return the `source_kind` of every registered parser."""
    return [p.source_kind for p in _PARSERS]


def parse_informe(content: str, source_kind: str | None = None) -> list[FieldMapping]:
    """Map an informe's text to suggested declaration fields.

    If `source_kind` is given, that parser is used. Otherwise the most
    recently registered parser whose `detect` returns True wins. Raises
    LookupError if no parser matches.
    """
    if source_kind is not None:
        for p in _PARSERS:
            if p.source_kind == source_kind:
                return p.parse(content)
        raise LookupError(
            f"No parser registered for source_kind={source_kind!r}. "
            f"Available: {available_sources()}"
        )

    for p in reversed(_PARSERS):
        if p.detect(content):
            return p.parse(content)
    raise LookupError(
        "No registered parser recognized this informe. "
        f"Available sources: {available_sources() or '(none yet)'}"
    )
