"""Tool implementations: pure functions, called from `server.py` and tests."""

from __future__ import annotations

import re
import unicodedata
from functools import cache
from pathlib import Path

from irpf_core import (
    Declaration,
    OpaqueRecord,
    TypedRecord,
    decode,
    encode,
    field_str,
    validate_value,
)
from irpf_core.informes import available_sources, parse_informe
from irpf_core.informes.detect import detect_sources as _detect_sources
from irpf_knowledge import load_leiaute, load_perguntas, record_layout


def decode_declaration(path: str) -> dict:
    decl = decode(Path(path).expanduser())
    serialized = [_serialize_record(r) for r in decl.records]
    # `header` and `identificacao` reference the SAME dicts that live in
    # `records`, so editing a field through either view reaches encode().
    header = next((s for s in serialized if s["identificador"] == "IR"), None)
    identificacao = next((s for s in serialized if s["identificador"] == "16"), None)
    return {
        "tax_year": 2026,
        "header": header,
        "identificacao": identificacao,
        "records": serialized,
    }


def _serialize_record(r: TypedRecord | OpaqueRecord) -> dict:
    if isinstance(r, OpaqueRecord):
        return {
            "identificador": r.identificador,
            "nome": "REG_OPAQUE",
            "fields": {"_raw": r.raw.decode("ascii", errors="replace")},
        }
    return {
        "identificador": r.identificador,
        "nome": r.nome,
        "fields": {k: v.decode("ascii") for k, v in r.fields.items()},
    }


def explain_field(record_type: str, field_name: str | None = None) -> dict:
    layout = record_layout(record_type)
    if field_name is None:
        return {
            "identificador": record_type,
            "nome": layout["nome"],
            "descricao": layout["descricao"],
            "tamanho_total": layout["tamanho_total"],
            "campos": layout["campos"],
        }
    for campo in layout["campos"]:
        if campo["nome"] == field_name:
            return {
                "record": {
                    "identificador": record_type,
                    "nome": layout["nome"],
                    "descricao": layout["descricao"],
                },
                "field": campo,
            }
    raise KeyError(
        f"Field {field_name!r} not found in record {record_type} ({layout['nome']})"
    )


def list_record_types() -> list[dict]:
    leiaute = load_leiaute()["records"]
    return [
        {
            "identificador": ident,
            "nome": layout["nome"],
            "descricao": layout["descricao"],
            "tamanho_total": layout["tamanho_total"],
            "field_count": len(layout["campos"]),
        }
        for ident, layout in leiaute.items()
    ]


DISCLAIMER = (
    "Valores extraídos diretamente da declaração já calculada pelo programa "
    "oficial IRPF 2026. Este resumo é informativo — sempre confira no programa "
    "oficial antes de transmitir."
)


def encode_declaration(declaration: dict, output_path: str) -> dict:
    """Re-serialize a (possibly modified) decoded declaration to a .DBK file.

    `declaration` must have the shape returned by decode_declaration():
    a 'records' list of {identificador, nome, fields:{name:str}}. Field
    string values must keep their exact on-disk width (numerics zero-padded,
    alpha space-padded) — pass them back as decode_declaration returned them,
    modifying only the content you intend to change while preserving length.
    """
    records: list[TypedRecord | OpaqueRecord] = []
    for rec in declaration["records"]:
        if rec.get("nome") == "REG_OPAQUE":
            raw = rec["fields"]["_raw"].encode("ascii")
            records.append(OpaqueRecord(identificador=rec["identificador"], raw=raw))
            continue
        fields = {k: v.encode("ascii") for k, v in rec["fields"].items()}
        records.append(TypedRecord(
            identificador=rec["identificador"],
            nome=rec["nome"],
            fields=fields,
        ))

    decl = Declaration(records=records)
    data = encode(decl)
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return {
        "path": str(out),
        "bytes_written": len(data),
        "record_count": len(records),
        "note": "Importe no programa oficial IRPF 2026 para validar antes de transmitir.",
    }


def tax_summary(path: str) -> dict:
    """Read the tax figures the official program already computed.

    Does NOT recompute tax — it surfaces the VR_* (monetary) values stored
    in the declaration's resumo records (REG_SIMPLES/REG_RESUMOSIMPLES for
    the simplified model, REG_COMPLETA/REG_RESUMOCOMPLETA for the complete
    model) plus the header, labeled with their leiaute descriptions.

    Returns {modelo, valores: [{campo, descricao, valor}], disclaimer}.
    """
    decl = decode(Path(path).expanduser())

    present = {r.identificador for r in decl.records if isinstance(r, TypedRecord)}
    if "20" in present or "19" in present:
        modelo = "completa"
        resumo_ids = ("19", "20")
    else:
        modelo = "simplificada"
        resumo_ids = ("17", "18")

    valores: list[dict] = []
    seen: set[str] = set()
    for ident in (*resumo_ids, "IR"):
        try:
            rec = decl.first(ident)
        except KeyError:
            continue
        layout = record_layout(ident)
        for campo in layout["campos"]:
            if (campo["tipo"] == "N" and campo.get("decimais") == 2
                    and campo["nome"].startswith("VR_")):
                raw = rec.fields.get(campo["nome"])
                if raw is None:
                    continue
                cents = int(raw.decode("ascii").strip() or "0")
                if cents == 0:
                    continue
                key = f"{ident}:{campo['nome']}"
                if key in seen:
                    continue
                seen.add(key)
                valores.append({
                    "record": rec.nome,
                    "campo": campo["nome"],
                    "descricao": campo["descricao"],
                    "valor": cents / 100.0,
                })

    return {
        "modelo": modelo,
        "valores": valores,
        "disclaimer": DISCLAIMER,
    }


def detect_sources(path: str) -> list[dict]:
    """List the institutions/payers a declaration references.

    Helps the user know which informes to gather and which source parsers
    are worth building.
    """
    decl = decode(Path(path).expanduser())
    return _detect_sources(decl)


def map_informe(content: str, source_kind: str | None = None) -> dict:
    """Map an informe document's text to suggested declaration fields.

    Routes to a registered parser (by `source_kind`, or auto-detected).
    Until a parser for the relevant source is registered, returns a
    structured 'unsupported' result listing the available sources — adding a
    parser requires a real sample of that informe.
    """
    try:
        mappings = parse_informe(content, source_kind=source_kind)
    except LookupError as e:
        return {
            "ok": False,
            "reason": str(e),
            "available_sources": available_sources(),
            "mappings": [],
        }
    return {
        "ok": True,
        "available_sources": available_sources(),
        "mappings": [m.as_dict() for m in mappings],
    }


def validate_field(record_type: str, field_name: str, value: str) -> dict:
    errors = validate_value(record_type, field_name, value)
    return {
        "record_type": record_type,
        "field_name": field_name,
        "value": value,
        "ok": not errors,
        "errors": errors,
    }


def sanity_check(path: str) -> list[dict]:
    """Cross-field consistency checks on a declaration.

    Returns a list of findings, each {level, record, field, message}.
    level is 'error' (definitely wrong) or 'warning' (suspicious).
    """
    decl = decode(Path(path).expanduser())
    findings: list[dict] = []

    header_cpf = field_str(decl.header, "NR_CPF")

    # 1) Every record's NR_CPF must match the header CPF.
    for r in decl.records:
        if isinstance(r, OpaqueRecord):
            continue
        if "NR_CPF" in r.fields:
            cpf = field_str(r, "NR_CPF")
            if cpf and cpf != header_cpf:
                findings.append({
                    "level": "error",
                    "record": r.nome,
                    "field": "NR_CPF",
                    "message": f"CPF {cpf} does not match header CPF {header_cpf}",
                })

    # 2) Bens (REG_BEM) with empty discriminação (TX_BEM).
    for bem in decl.all("27"):
        if "TX_BEM" in bem.fields and not field_str(bem, "TX_BEM"):
            findings.append({
                "level": "warning",
                "record": "REG_BEM",
                "field": "TX_BEM",
                "message": "Bem com discriminação (TX_BEM) vazia",
            })

    # 3) Pagamentos (REG_PAGAMENTO) referencing a payer with no CNPJ/CPF.
    for pag in decl.all("26"):
        cnpj_field = next((f for f in ("NR_CPFCNPJ", "NM_CPFCNPJ", "NR_CNPJ")
                           if f in pag.fields), None)
        if cnpj_field and not field_str(pag, cnpj_field):
            findings.append({
                "level": "warning",
                "record": "REG_PAGAMENTO",
                "field": cnpj_field,
                "message": "Pagamento sem CNPJ/CPF do beneficiário",
            })

    return findings


def diff_declarations(path_old: str, path_new: str) -> dict:
    """Compare two declarations and report what changed.

    Singleton records (header, identificacao, trailer) are diffed
    field-by-field. Multi-instance records are diffed by a stable key
    (all field values joined) so additions/removals are detected.
    """
    old = decode(Path(path_old).expanduser())
    new = decode(Path(path_new).expanduser())

    result: dict = {"singleton_changes": {}, "record_set_changes": {}}

    # Singleton field-level diffs.
    for ident in ("IR", "16", "T9"):
        try:
            old_rec = old.first(ident)
            new_rec = new.first(ident)
        except KeyError:
            continue
        changes = _diff_record_fields(old_rec, new_rec)
        if changes:
            result["singleton_changes"][old_rec.nome] = changes

    # Multi-instance record set diffs (by type).
    old_types = {r.identificador for r in old.records if isinstance(r, TypedRecord)}
    new_types = {r.identificador for r in new.records if isinstance(r, TypedRecord)}
    for ident in sorted(old_types | new_types):
        if ident in ("IR", "16", "T9"):
            continue
        old_keys = _record_keys(old.all(ident))
        new_keys = _record_keys(new.all(ident))
        added = sorted(new_keys - old_keys)
        removed = sorted(old_keys - new_keys)
        if added or removed or len(old_keys) != len(new_keys):
            layout = load_leiaute()["records"].get(ident, {})
            result["record_set_changes"][ident] = {
                "nome": layout.get("nome", ident),
                "count_old": len(old.all(ident)),
                "count_new": len(new.all(ident)),
                "added": len(added),
                "removed": len(removed),
            }

    return result


def _diff_record_fields(old: TypedRecord, new: TypedRecord) -> dict:
    changes = {}
    keys = list(dict.fromkeys([*old.fields, *new.fields]))
    for k in keys:
        if k.startswith("FILLER") or k == "NR_CONTROLE" or k == "NR_HASH":
            continue  # ignore padding / volatile control fields
        ov = old.fields.get(k, b"").decode("ascii").rstrip()
        nv = new.fields.get(k, b"").decode("ascii").rstrip()
        if ov != nv:
            changes[k] = {"old": ov, "new": nv}
    return changes


def _record_keys(records: list[TypedRecord]) -> set[str]:
    """Build a set of stable identity keys for a list of records, ignoring
    volatile fields (control numbers)."""
    keys = set()
    for r in records:
        parts = [
            v.decode("ascii").rstrip()
            for k, v in r.fields.items()
            if not k.startswith("FILLER") and k not in ("NR_CONTROLE", "NR_HASH")
        ]
        keys.add("|".join(parts))
    return keys


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _strip_accents(s: str) -> str:
    """Fold accented characters: 'previdência' → 'previdencia'."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if unicodedata.category(c) != "Mn"
    )


def _tokenize(s: str) -> list[str]:
    return _TOKEN_RE.findall(_strip_accents(s).lower())


@cache
def _perguntas_with_tokens() -> list[tuple[dict, set[str], str, str]]:
    """Pre-process every pergunta into (record, token_set, norm_title, norm_body).
    The normalized strings are accent-stripped and lowercased for fast matching.
    """
    out = []
    for p in load_perguntas():
        norm_title = _strip_accents(p["titulo"]).lower()
        norm_body = _strip_accents(p["resposta"]).lower()
        tokens = set(_tokenize(p["titulo"] + " " + p["resposta"]))
        out.append((p, tokens, norm_title, norm_body))
    return out


def lookup_pergunta(query: str, top_k: int = 5) -> list[dict]:
    """Keyword search ranked by query-term coverage, then by TF.

    Score formula favors docs that contain MORE DISTINCT query tokens
    (coverage) over docs that just repeat one common token many times:

        score = (distinct title tokens) * 100
              + (distinct body tokens)  * 10
              + (total token occurrences in body)

    A doc matching all 3 query tokens always beats one matching just 1
    token, regardless of repetition count. Title hits are heavily weighted.
    """
    query_tokens = list(dict.fromkeys(_tokenize(query)))  # dedup, preserve order
    if not query_tokens:
        return []

    scored = []
    for p, doc_tokens, norm_title, norm_body in _perguntas_with_tokens():
        distinct_title = sum(1 for t in query_tokens if t in norm_title)
        distinct_body = sum(1 for t in query_tokens if t in doc_tokens)
        tf = sum(norm_body.count(t) for t in query_tokens if t in doc_tokens)

        if distinct_body == 0:
            continue

        score = distinct_title * 100 + distinct_body * 10 + tf
        scored.append((score, p))

    scored.sort(key=lambda x: (-x[0], x[1]["num"]))
    return [
        {
            "num": p["num"],
            "titulo": p["titulo"],
            "resposta": p["resposta"],
            "score": score,
        }
        for score, p in scored[:top_k]
    ]
