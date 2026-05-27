---
name: irpf-decode
description: Use when the user wants to read, inspect, or summarize a Brazilian IRPF declaration file (.DBK / .DEC). Decodes the file into structured data and presents a human summary.
---

# irpf-decode

Decode and summarize an IRPF 2026 declaration file.

## When to use

The user points at a `.DBK` or `.DEC` file and wants to know what's in it —
"what does my declaration say", "summarize my IR", "show my assets", etc.

## Prerequisites

The `irpf-mentor` MCP server must be connected. It exposes `decode`, `explain`,
and `list_records`.

## Workflow

1. Call `decode(path)` with the absolute path to the user's file.
2. From the returned structure, summarize for the user:
   - **Identificação**: name, CPF, UF, birth date (from the `16` record /
     `identificacao`). Strip trailing spaces from alpha fields.
   - **Modelo**: simplificada (records `17`/`18` present) or completa
     (`19`/`20`).
   - **Bens e Direitos** (`27` records): count, and a line each with CD_BEM +
     a short slice of TX_BEM + VR_ATUAL (divide stored integer by 100 for R$).
   - **Pagamentos** (`26` records): count and total.
   - **Rendimentos isentos / exclusivos** (`23` / `24`).
3. When a field's meaning is unclear, call `explain(record_type, field_name)`
   to get the official description before explaining it to the user.

## Money formatting

Numeric fields with 2 decimals store cents as an integer string with leading
zeros (e.g. `0000004528657` = R$ 45.286,57). Always divide by 100 and format
in Brazilian style.

## Privacy

This reads a file containing real PII. Never write its contents anywhere the
user didn't ask for. Don't echo the full CPF unless the user asks.
