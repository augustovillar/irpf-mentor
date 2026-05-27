---
name: irpf-fill
description: Use when the user wants help filling or editing their IRPF declaration — adding/correcting a field, then producing an importable .DBK. Guides the edit and writes the file with explicit confirmation.
---

# irpf-fill

Guided editing of an IRPF declaration, producing an importable `.DBK`.

## When to use

"Add this asset", "fix the value in bens", "update my address", "produce a
.DBK I can import with this change".

## Prerequisites

The `irpf-mentor` MCP server must be connected (`decode`, `explain`,
`validate`, `encode`).

## Workflow

1. `decode(path)` to load the current declaration as structured JSON.
2. Identify the target record and field with the user. Use `explain` to
   confirm the field's type, size, and meaning before touching it.
3. For each value the user wants to set:
   - Call `validate(record_type, field_name, value)` FIRST. If it returns
     `ok=false`, tell the user the errors and don't proceed with that value.
   - Format the value to the field's exact on-disk width: numerics are
     zero-padded on the left to `tamanho` (and store cents for 2-decimal
     fields — R$ 1.234,56 → `000000123456`); alpha is space-padded on the
     right. The string you put in `fields[name]` MUST be exactly `tamanho`
     characters.
4. **Confirmation gate**: before writing, show the user a before/after of
   every field you changed and get explicit approval.
5. `encode(declaration, output_path)` to write the new `.DBK`.
6. Tell the user to import it into the official IRPF 2026 program
   ("Importar Declaração") and re-run "Verificar pendências" — totals,
   hashes and the trailer are NOT recomputed by this tool, so the official
   program must finalize the file.

## Hard rules

- Never change a field width. The file is fixed-width; a wrong length
  corrupts every following record.
- Never invent values. Only set what the user explicitly provides.
- This tool does not recompute tax totals or the integrity hash. Always end
  by directing the user back to the official program to validate.
