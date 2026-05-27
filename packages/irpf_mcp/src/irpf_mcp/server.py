"""irpf-mentor MCP server: exposes IRPF 2026 knowledge & decoding to LLMs.

Each tool is implemented as a thin wrapper over `irpf_core` and
`irpf_knowledge`. The MCP layer doesn't know any IRPF business rules —
it only marshals types and surfaces tools.

Run the server (stdio transport, suitable for Claude Code & Codex):

    uv run irpf-mcp
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools import (
    decode_declaration,
    detect_sources,
    diff_declarations,
    encode_declaration,
    explain_field,
    list_record_types,
    lookup_pergunta,
    map_informe,
    sanity_check,
    tax_summary,
    validate_field,
)

mcp = FastMCP("irpf-mentor")


@mcp.tool()
def decode(path: str) -> dict:
    """Parse a .DBK / .DEC declaration file and return its structured contents.

    Returns a dict shaped:
        {
          "tax_year": 2026,
          "header": {fields_dict},
          "identificacao": {fields_dict},
          "records": [{identificador, nome, fields}, ...]
        }

    Field values are returned as strings; numeric fields keep their leading
    zeros, alpha fields keep trailing-space padding (use accessors locally
    if you need stripped values).

    Args:
        path: Absolute path to a .DBK or .DEC file. The file must be a real
              IRPF 2026 declaration; older years are not yet supported.
    """
    return decode_declaration(path)


@mcp.tool()
def explain(record_type: str, field_name: str | None = None) -> dict:
    """Authoritative explanation of a record type or a specific field.

    Args:
        record_type: Leiaute identifier — 'IR' (REG_HEADER), '16'
                     (REG_IDENTIFICACAO), '26' (REG_PAGAMENTO), '27'
                     (REG_BEM), 'T9' (REG_TRAILLER), etc. Run list_records()
                     to see all 86.
        field_name:  Optional. If given, returns only that field's spec.
                     If omitted, returns the whole record's layout.

    Returns the leiaute spec (nome, tipo, tamanho, offset, decimals,
    descricao) sourced from the official irpf.jar.
    """
    return explain_field(record_type, field_name)


@mcp.tool()
def list_records() -> list[dict]:
    """List every record type known to the leiaute (86 entries for 2026).

    Returns: [{identificador, nome, descricao, tamanho_total, field_count}]
    """
    return list_record_types()


@mcp.tool()
def lookup_perguntas(query: str, top_k: int = 5) -> list[dict]:
    """Keyword search over the official RFB Perguntas e Respostas IRPF 2026.

    V1 uses simple case-insensitive substring matching with term-frequency
    ranking. A future version will swap in semantic embeddings.

    Args:
        query:  Natural-language query in Portuguese (e.g. "previdencia
                privada PGBL", "declarar carro financiado").
        top_k:  Number of results (default 5, max 20).

    Returns a list of {num, titulo, resposta, score} sorted by relevance.
    """
    return lookup_pergunta(query, top_k=min(top_k, 20))


@mcp.tool()
def validate(record_type: str, field_name: str, value: str) -> dict:
    """Check whether a value is acceptable for a given record field.

    Re-implements the official CampoTXT validation: numeric fields must be
    digits within the declared size/decimals, alpha fields within max length,
    dates as DDMMAAAA, indicators as S/N/0/1.

    Args:
        record_type: Leiaute identifier (e.g. '16', '27').
        field_name:  Field name within that record (e.g. 'NR_CPF', 'VR_ATUAL').
        value:       The logical value to test (digits for numerics, text for
                     alpha — no on-disk padding).

    Returns {ok: bool, errors: [str]}.
    """
    return validate_field(record_type, field_name, value)


@mcp.tool()
def sanity(path: str) -> list[dict]:
    """Run cross-field consistency checks on a declaration file.

    Flags issues like CPF mismatches between records, bens with empty
    discriminação, and pagamentos missing the beneficiary CNPJ/CPF.

    Args:
        path: Absolute path to a .DBK / .DEC file.

    Returns a list of {level: 'error'|'warning', record, field, message}.
    """
    return sanity_check(path)


@mcp.tool()
def diff(path_old: str, path_new: str) -> dict:
    """Compare two declaration files and report what changed.

    Singleton records (header, identificação, trailer) are diffed
    field-by-field (ignoring padding and volatile control numbers);
    multi-instance records (bens, pagamentos, …) are diffed by count and
    by added/removed instances.

    Args:
        path_old: Path to the earlier declaration (e.g. last year's .DEC).
        path_new: Path to the later declaration (e.g. this year's draft).

    Returns {singleton_changes: {...}, record_set_changes: {...}}.
    """
    return diff_declarations(path_old, path_new)


@mcp.tool()
def encode(declaration: dict, output_path: str) -> dict:
    """Write a (possibly edited) decoded declaration back to a .DBK file.

    Pass the same structure that decode() returned, with any field values
    you changed kept at their exact on-disk width (numerics zero-padded,
    alpha space-padded). The result imports into the official IRPF 2026
    program.

    Args:
        declaration: A dict shaped like decode()'s output.
        output_path: Where to write the .DBK.

    Returns {path, bytes_written, record_count, note}.
    """
    return encode_declaration(declaration, output_path)


@mcp.tool()
def tax(path: str) -> dict:
    """Surface the tax figures the official program already computed.

    This does NOT recompute tax — it reads the stored VR_* values from the
    declaration's resumo records and header (always accurate, since the
    official program produced them). Every response carries a disclaimer.

    Args:
        path: Absolute path to a .DBK / .DEC file.

    Returns {modelo, valores: [{record, campo, descricao, valor}], disclaimer}.
    """
    return tax_summary(path)


@mcp.tool()
def sources(path: str) -> list[dict]:
    """List the institutions/payers referenced in a declaration.

    Useful before a fill workflow: tells the user which informes to gather
    (banks, corretoras, clínicas) based on what's already in their file.

    Args:
        path: Absolute path to a .DBK / .DEC file.

    Returns [{nome, cnpj, records:[{identificador, nome_registro}]}].
    """
    return detect_sources(path)


@mcp.tool()
def map_document(content: str, source_kind: str | None = None) -> dict:
    """Map an informe document (pasted text) to suggested declaration fields.

    Routes to a registered source parser. No concrete parsers ship yet —
    each needs a real sample informe to build against — so this currently
    returns an 'unsupported' result listing available sources.

    Args:
        content:     The informe's text content.
        source_kind: Optional explicit parser slug; otherwise auto-detected.

    Returns {ok, mappings:[{ficha, record_type, field_name, value,
    confidence, note}], available_sources}.
    """
    return map_informe(content, source_kind=source_kind)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
