"""Detect which informe sources a declaration references.

Scans a parsed Declaration for the institutions/payers that appear in it —
medical providers in pagamentos, financial institutions in bens and in
exempt/exclusive-income records. This tells the user which informes they
should gather, and which source parsers would be worth building.
"""

from __future__ import annotations

from typing import Any

from ..accessors import field_str
from ..schema import Declaration, TypedRecord

# Records that reference an external institution, and the field(s) that name
# it / identify it. Kept small and explicit rather than guessing across all 86.
_NAME_FIELDS = ("NM_BENEF", "NM_NOME", "NM_FONTE", "NM_PAGADORA", "NM_PAGADOR")
_ID_FIELDS = ("NM_CPFCNPJ", "NR_CNPJ", "NR_CPFCNPJ", "NR_CPF_CNPJ")

# Records that describe the taxpayer themselves, not an external institution.
_SELF_RECORDS = ("IR", "16")


def detect_sources(decl: Declaration) -> list[dict[str, Any]]:
    """Return distinct institutions referenced, with the records that cite them.

    Each entry: {nome, cnpj, records: [{identificador, nome_registro}]}.
    """
    found: dict[tuple[str, str], dict[str, Any]] = {}

    for r in decl.records:
        if not isinstance(r, TypedRecord):
            continue
        if r.identificador in _SELF_RECORDS:
            continue
        nome = _first_nonempty(r, _NAME_FIELDS)
        cnpj = _first_nonempty(r, _ID_FIELDS)
        # Ignore the titular's own CPF appearing as an id.
        if cnpj and len(cnpj) == 11:
            cnpj = ""
        if not nome and not cnpj:
            continue
        key = (nome, cnpj)
        entry = found.setdefault(key, {"nome": nome, "cnpj": cnpj, "records": []})
        entry["records"].append({
            "identificador": r.identificador,
            "nome_registro": r.nome,
        })

    return list(found.values())


def _first_nonempty(rec: TypedRecord, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in rec.fields:
            v = field_str(rec, name)
            if v:
                return v
    return ""
