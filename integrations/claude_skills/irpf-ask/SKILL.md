---
name: irpf-ask
description: Use when the user asks a question about Brazilian income tax (IRPF) rules, how to declare something, deductions, deadlines, or form fields. Answers authoritatively from Receita Federal sources and always cites them.
---

# irpf-ask

Answer IRPF 2026 questions authoritatively — never from memory or guesswork.

## When to use

Any "como declaro…", "posso deduzir…", "qual o limite de…", "preciso
declarar…" type question about Brazilian personal income tax.

## Prerequisites

The `irpf-mentor` MCP server must be connected. It exposes `lookup_perguntas`
(search over the official RFB Perguntas e Respostas) and `explain` (official
field layout + descriptions).

## Workflow

1. Call `lookup_perguntas(query, top_k=5)` with the user's question rephrased
   as Portuguese keywords (e.g. "previdência privada PGBL dedução limite").
2. Read the returned Q&As. Synthesize an answer **grounded in them**.
3. If the question is about a specific form field, also call
   `explain(record_type, field_name)` for the authoritative field description.

## Hard rules

- **Always cite the source.** Every claim must reference the pergunta number
  (e.g. "conforme a Pergunta 335 do Perguntas e Respostas IRPF 2026") or the
  leiaute field. If `lookup_perguntas` returns nothing relevant, SAY SO —
  do not fabricate an answer from general knowledge.
- If the top results don't actually answer the question, tell the user the
  official Q&A doesn't cover it and suggest they confirm with a contador or
  the Receita Federal directly.
- Keyword search can miss things; if the user's phrasing yields weak results,
  try alternative Portuguese terms before concluding nothing exists.
- End substantive answers with: "Confirme no programa oficial IRPF 2026 ou com
  um contador antes de transmitir."
