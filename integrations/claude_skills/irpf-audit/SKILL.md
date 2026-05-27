---
name: irpf-audit
description: Use when the user wants to sanity-check or audit an IRPF declaration for inconsistencies before transmitting (CPF mismatches, empty asset descriptions, missing payer CNPJs, etc.).
---

# irpf-audit

Run consistency checks on an IRPF declaration and report findings.

## When to use

"Check my declaration for errors", "is anything wrong before I send it",
"audit my IR draft".

## Prerequisites

The `irpf-mentor` MCP server must be connected (`sanity`, `decode`, `explain`,
`tax`).

## Workflow

1. Call `sanity(path)` on the user's file.
2. Group findings by `level`:
   - **error**: definitely wrong (e.g. a record's CPF doesn't match the
     header). These must be fixed.
   - **warning**: suspicious but possibly intentional (e.g. a bem with empty
     discriminação, a pagamento with no beneficiary CNPJ).
3. For each finding, explain in plain Portuguese what it means and how to fix
   it in the official program (which ficha/campo).
4. Optionally call `tax(path)` and present the computed totals so the user
   sees the imposto a pagar/restituir alongside the audit.

## Important

`sanity` covers structural consistency, not full legal correctness. Always
tell the user this is not a substitute for review by a contador, and that the
official program's own validation ("Verificar pendências") is authoritative.
