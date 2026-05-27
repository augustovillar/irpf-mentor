---
name: irpf-diff
description: Use when the user wants to compare two IRPF declarations (e.g. this year vs last year, or a draft vs the transmitted version) and see what changed.
---

# irpf-diff

Compare two IRPF declaration files and explain the differences.

## When to use

"What changed since last year", "compare my draft to what I transmitted",
"did I forget to carry over an asset", etc.

## Prerequisites

The `irpf-mentor` MCP server must be connected (`diff`, `decode`, `explain`).

## Workflow

1. Confirm the two file paths with the user (which is older, which is newer).
2. Call `diff(path_old, path_new)`.
3. Present the result in two parts:
   - **Singleton changes** (`singleton_changes`): field-level changes to the
     header / identificação / trailer. Use `explain` to label any cryptic
     field name. Flag changes to name, UF, bank account, or marital status.
   - **Record-set changes** (`record_set_changes`): per record type, how many
     instances were added/removed (e.g. "2 bens added, 1 removed";
     "1 fewer pagamento"). For each changed type, decode both files and show
     which specific items differ if the user wants detail.
4. Proactively flag suspicious deltas: assets that disappeared, dependents
   removed, large swings in totals.

## Note

`diff` intentionally ignores volatile control fields (NR_CONTROLE, NR_HASH)
and FILLER padding, so reported changes are meaningful.
