from __future__ import annotations

from .schema import Declaration, OpaqueRecord, TypedRecord


def encode(decl: Declaration) -> bytes:
    """Serialize a Declaration back to .DBK / .DEC bytes.

    Each record is terminated by CRLF, matching the on-disk format produced
    by the official IRPF 2026 program. For `TypedRecord` we concatenate the
    field byte slices in leiaute order; for `OpaqueRecord` we emit the raw
    bytes as captured.
    """
    out = bytearray()
    for r in decl.records:
        out += _encode_record(r)
        out += b"\r\n"
    return bytes(out)


def _encode_record(r: TypedRecord | OpaqueRecord) -> bytes:
    if isinstance(r, OpaqueRecord):
        return r.raw
    return b"".join(r.fields.values())
