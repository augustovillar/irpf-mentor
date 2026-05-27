"""Schema for IRPF declarations parsed against the leiaute.

Every record in a .DBK is laid out as a fixed-width sequence of fields
described by `irpf_knowledge.load_leiaute()`. We don't model each of the 86
record types as a separate pydantic class — they share the same shape (an
ordered dict of named byte slices), and 86 nearly-identical classes would
be noise. Instead, `TypedRecord` holds the raw byte slice per field and
defers semantic interpretation to typed accessors (`field_str`, `field_int`,
`field_decimal`, `field_date`, `field_bool`) that consult the leiaute.

The encoded byte representation is recovered by concatenating the field
values in leiaute order — round-trip is bit-perfect by construction
because we store the original bytes verbatim.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

UNKNOWN_RECORD_NAME = "REG_UNKNOWN"
"""Reserved nome used when a record's identifier isn't in the leiaute (e.g.
a future record type appears in someone's .DBK before we bump the leiaute).
Such records still round-trip — their raw bytes are stored in
`OpaqueRecord` and emitted unchanged."""


class TypedRecord(BaseModel):
    """A .DBK record parsed against the leiaute.

    `fields` is an ordered dict (insertion order = leiaute order) of
    `field_name → raw_bytes_slice`. Encoding == ``b"".join(fields.values())``.
    """

    model_config = ConfigDict(extra="forbid")

    identificador: str = Field(min_length=2, max_length=4)
    """The leiaute identifier of this record (e.g. 'IR', '16', '27', 'T9').
    'IR' is the file header (4-byte prefix 'IRPF' in bytes); other codes are
    2 chars."""

    nome: str
    """The leiaute name (e.g. 'REG_HEADER', 'REG_IDENTIFICACAO', 'REG_BEM')."""

    fields: dict[str, bytes]
    """Field name → raw byte slice. Length and order follow the leiaute."""


class OpaqueRecord(BaseModel):
    """Fallback for records whose identifier is missing from the leiaute.

    Kept so a parser run against a slightly newer .DBK than the leiaute
    knows about still round-trips. Shouldn't happen in normal operation.
    """

    model_config = ConfigDict(extra="forbid")

    identificador: str
    raw: bytes


class Declaration(BaseModel):
    """A complete IRPF declaration parsed from a .DBK / .DEC file.

    Records are kept in original on-disk order. The file header (REG_HEADER,
    identificador 'IR') is conventionally first; the trailer (REG_TRAILLER,
    'T9') is conventionally last.
    """

    model_config = ConfigDict(extra="forbid")

    records: list[TypedRecord | OpaqueRecord] = Field(default_factory=list)

    def first(self, identificador: str) -> TypedRecord:
        """Return the first record matching the given identificador.

        Raises KeyError if none found.
        """
        for r in self.records:
            if isinstance(r, TypedRecord) and r.identificador == identificador:
                return r
        raise KeyError(f"No record with identificador={identificador!r}")

    def all(self, identificador: str) -> list[TypedRecord]:
        """Return every record matching the given identificador, in order."""
        return [r for r in self.records
                if isinstance(r, TypedRecord) and r.identificador == identificador]

    @property
    def header(self) -> TypedRecord:
        """The REG_HEADER record (identificador 'IR')."""
        return self.first("IR")

    @property
    def identificacao(self) -> TypedRecord:
        """The REG_IDENTIFICACAO record (identificador '16')."""
        return self.first("16")

    @property
    def trailer(self) -> TypedRecord:
        """The REG_TRAILLER record (identificador 'T9')."""
        return self.first("T9")
