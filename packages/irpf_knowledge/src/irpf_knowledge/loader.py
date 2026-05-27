from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

SUPPORTED_TAX_YEARS = (2026,)


@cache
def load_leiaute(tax_year: int = 2026) -> dict[str, Any]:
    """Load the JAR-derived record layout for a given IRPF tax year.

    Structure:
        {
            "tax_year": 2026,
            "ano_base": 2025,
            "tipo_arquivo": "ARQ_IRPF",
            "records": {
                "IR": {
                    "nome": "REG_HEADER",
                    "descricao": "01 HEADER - IDENTIFICAÇÂO DA DECLARAÇÂO",
                    "tamanho_total": 1244,
                    "campos": [
                        {"nome": "SISTEMA", "tipo": "C", "tamanho": 8,
                         "offset": 0, "descricao": "..."},
                        ...
                    ],
                },
                "16": {...},  # REG_IDENTIFICACAO
                ...
            }
        }

    Result is cached — safe to call from hot paths.
    """
    if tax_year not in SUPPORTED_TAX_YEARS:
        raise ValueError(
            f"Tax year {tax_year} not supported; have data for: {SUPPORTED_TAX_YEARS}"
        )
    resource = files("irpf_knowledge").joinpath(f"data/{tax_year}/leiaute_2026.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def record_layout(identificador: str, tax_year: int = 2026) -> dict[str, Any]:
    """Convenience: fetch the layout dict for one record (e.g. 'IR', '16', 'T9')."""
    recs = load_leiaute(tax_year)["records"]
    if identificador not in recs:
        raise KeyError(
            f"Record identifier {identificador!r} not in leiaute for {tax_year}"
        )
    return recs[identificador]


@cache
def load_perguntas(tax_year: int = 2026) -> list[dict[str, Any]]:
    """Load the RFB Perguntas e Respostas Q&A as a list of dicts.

    Each entry has shape `{"num": int, "titulo": str, "resposta": str}`.
    For 2026 there are ~734 entries (the official PDF advertises 745; the
    splitter regex misses a small number due to layout variations and will
    be improved over time). Cached.
    """
    if tax_year not in SUPPORTED_TAX_YEARS:
        raise ValueError(
            f"Tax year {tax_year} not supported; have data for: {SUPPORTED_TAX_YEARS}"
        )
    resource = files("irpf_knowledge").joinpath(f"data/{tax_year}/perguntas_2026.jsonl")
    return [json.loads(line) for line in resource.read_text(encoding="utf-8").splitlines() if line.strip()]


@cache
def load_ajuda(tax_year: int = 2026) -> str:
    """Load the AjudaIRPF Markdown for a tax year.

    Sourced from Docling conversion of the bundled `AjudaIRPF.pdf` (the
    official help PDF shipped with the IRPF program). Tables are preserved
    as Markdown tables. ~895 KB / ~10k lines for 2026.

    Returned as a single string; cached.
    """
    if tax_year not in SUPPORTED_TAX_YEARS:
        raise ValueError(
            f"Tax year {tax_year} not supported; have data for: {SUPPORTED_TAX_YEARS}"
        )
    resource = files("irpf_knowledge").joinpath(f"data/{tax_year}/ajuda_2026.md")
    return resource.read_text(encoding="utf-8")
