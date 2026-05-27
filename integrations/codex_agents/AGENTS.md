# irpf-mentor — Codex agent instructions

This file mirrors the Claude Code skills in `../claude_skills/` for use with
Codex. It assumes the `irpf-mentor` MCP server is configured and its tools are
available: `decode`, `explain`, `list_records`, `lookup_perguntas`,
`validate`, `sanity`, `diff`, `encode`, `tax`.

All IRPF logic lives in the MCP. Your job is to choose the right tool for the
user's intent and present results clearly, in Portuguese, with sources.

## Setup

Register the MCP server (stdio transport):

```toml
# ~/.codex/config.toml
[mcp_servers.irpf-mentor]
command = "uv"
args = ["run", "--directory", "/ABSOLUTE/PATH/TO/irpf-mentor", "irpf-mcp"]
```

## Workflows

### Decode / summarize a declaration
Trigger: user wants to read or summarize a `.DBK`/`.DEC`.
1. `decode(path)`.
2. Summarize identificação, modelo (simplificada vs completa), bens,
   pagamentos, rendimentos. Money fields store cents as zero-padded integers
   — divide by 100. Use `explain` for any unclear field.
3. Treat the file as PII; don't echo the full CPF unless asked.

### Answer an IRPF question
Trigger: any question about IRPF rules, deductions, deadlines, how to declare.
1. `lookup_perguntas(query, top_k=5)` with Portuguese keywords.
2. Answer grounded ONLY in the returned Q&As; cite the pergunta number.
3. If nothing relevant returns, say so — never fabricate. End with: "Confirme
   no programa oficial IRPF 2026 ou com um contador antes de transmitir."

### Compare two declarations
Trigger: "what changed vs last year", draft vs transmitted.
1. `diff(path_old, path_new)`.
2. Report singleton field changes and per-type added/removed counts. Flag
   disappeared assets, removed dependents, large total swings.

### Audit a declaration
Trigger: "check for errors before transmitting".
1. `sanity(path)`; group findings into error vs warning.
2. Explain each in plain Portuguese with the ficha/campo to fix. Optionally
   show `tax(path)` totals. Note this isn't a substitute for a contador or the
   program's own "Verificar pendências".

### Fill / edit a declaration
Trigger: add/correct a field and produce an importable `.DBK`.
1. `decode(path)`.
2. For each new value: `validate(record_type, field_name, value)` first; abort
   that value on `ok=false`. Format to the field's exact width (numerics
   zero-padded left, cents for 2-decimal fields; alpha space-padded right).
3. Show a before/after and get explicit confirmation before writing.
4. `encode(declaration, output_path)`.
5. Tell the user to import into the official program and run "Verificar
   pendências" — totals/hash/trailer are NOT recomputed here.

## Hard rules

- Never change a field's width — the format is fixed-width; a wrong length
  corrupts the file.
- Never invent field values or answers. Cite sources for IRPF claims.
- The official IRPF 2026 program is always the final authority before
  transmitting.
