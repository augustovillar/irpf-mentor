# irpf-mentor — Design & Implementation Plan

**Repo:** `~/irpf-mentor/` (currently empty, will be initialized as Python uv monorepo + git repo)
**Date:** 2026-05-26
**Tax year scope:** IRPF 2026 (ano-base 2025)

---

## Context

The user wants to facilitate the Brazilian *Imposto de Renda* declaration process. They already have:

- The official **IRPF 2026** app installed at [~/ProgramasRFB/IRPF2026/](~/ProgramasRFB/IRPF2026/)
- Their real 2025 backup file at `~/personal/<CPF>-IRPF-A-2026-2025-ORIGI.DBK` (PII — never committed; CPF redacted from this doc)

Goal: build a Python **MCP server** (`irpf-mcp`) plus a matched set of **Claude Code skills** and **Codex agents** that together let an LLM:

1. **Decode** a `.DBK`/`.DEC` into structured JSON
2. **Answer IRPF questions authoritatively** (RFB Perguntas e Respostas + decompiled validators)
3. **Fill from source documents** (informe de rendimentos PJ, banco, corretora → ficha/linha)
4. **Diff year-over-year** declarations and flag anomalies

The MCP is the single source of truth; skills/agents are thin orchestration wrappers.

**Why this is feasible:** the `.DBK` is plain ASCII fixed-width text (verified: header begins `IRPF    20262025...`), the IRPF 2026 app is Java (`irpf.jar` + `lib-modulos/*.jar`) and decompilable with CFR, RFB publishes the authoritative *Leiaute do IRPF* and *Perguntas e Respostas* as PDFs, and the bundled `help/AjudaIRPF.pdf` (4.5 MB) covers every form field.

---

## Architecture

### Repo layout (Python uv monorepo)

```
irpf-mentor/
├── pyproject.toml              # uv workspace root
├── README.md
├── NOTICE.md                   # reverse-engineering / fair-use statement
├── .gitignore                  # blocks *.DBK / *.DEC / *.REC outside fixtures/
├── packages/
│   ├── irpf_core/              # Pure library: schema, .DBK parser/encoder, validators, calc.
│   │   ├── pyproject.toml      #   No MCP, no network. Importable standalone.
│   │   └── src/irpf_core/
│   ├── irpf_knowledge/         # Generated data committed to repo.
│   │   ├── pyproject.toml      #   data/2026/leiaute_2026.json,
│   │   └── src/irpf_knowledge/ #              perguntas_2026.jsonl,
│   │       └── data/2026/      #              ajuda_2026.md,
│   │                           #              jar_field_map_2026.json
│   └── irpf_mcp/               # MCP server. Wraps core + knowledge.
│       ├── pyproject.toml
│       └── src/irpf_mcp/
├── extractors/                 # Build-time scripts (NOT shipped to MCP consumers).
│   ├── decompile_jars.py       #   CFR → field constants, validators, calc methods
│   ├── parse_ajuda_pdf.py      #   Docling → ajuda_2026.md (tables preserved)
│   ├── parse_perguntas.py      #   Docling → md → split into perguntas_2026.jsonl
│   └── parse_leiaute.py        #   Docling → leiaute tables → leiaute_2026.json
├── integrations/
│   ├── claude_skills/          # Claude Code skill .md files
│   │   ├── irpf-decode/SKILL.md
│   │   ├── irpf-ask/SKILL.md
│   │   ├── irpf-fill/SKILL.md
│   │   ├── irpf-diff/SKILL.md
│   │   └── irpf-audit/SKILL.md
│   └── codex_agents/           # Codex AGENTS.md mirrors
├── fixtures/                   # SYNTHETIC ONLY, committed
│   └── synthetic-2026.dbk
├── tools/
│   └── redact.py               # CLI: real .DBK → synthetic fixture (used locally only)
└── docs/
    └── superpowers/specs/
        └── 2026-05-26-irpf-mentor-design.md   # Copy of this design, lives in repo
```

### Layer invariants

- **`irpf_core` knows nothing about MCP.** Could be used from a Jupyter notebook.
- **`irpf_knowledge` is a committed artifact.** Extractors run rarely; MCP boots instantly with zero PDF parsing at runtime.
- **Skills/agents are prompts, not code.** Every piece of IRPF logic lives in the MCP.
- **Year-versioned from day one.** `data/2026/` → 2027 is additive, not a migration.
- **Docling is an extractor-only dependency** — MCP runtime stays lean (no torch, no models).

### MCP tool surface (V1)

| Tool | Signature | Purpose |
|---|---|---|
| `decode_declaration` | `(path) → DeclarationJSON` | Parse `.DBK`/`.DEC` into typed JSON: identificacao, dependentes, rendimentos_pj, rendimentos_pf, rendimentos_isentos, bens, dividas, pagamentos, doacoes, renda_variavel, carne_leao, atividade_rural |
| `encode_declaration` | `(DeclarationJSON) → bytes` | Round-trip: emit a valid `.DBK` importable into IRPF2026 |
| `explain_field` | `(ficha, linha) → {description, official_help, validation, examples}` | Authoritative explanation merged from Ajuda + Leiaute + JAR validators |
| `lookup_pergunta` | `(query, top_k=5) → [{num, titulo, resposta, ficha_refs}]` | Semantic + keyword search over RFB Perguntas-e-Respostas |
| `validate_field` | `(ficha, linha, value, context?) → {ok, errors[]}` | Re-implementation of RFB validators from decompiled JAR logic |
| `diff_declarations` | `(old_path, new_path) → StructuredDiff` | Field-level diff with semantic groupings (assets ±, dependent CPF changes, income deltas %) |
| `sanity_check` | `(DeclarationJSON) → [{level, ficha, linha, message}]` | Cross-field checks (bem without acquisition cost, duplicate dependentes, IRRF without source CNPJ, etc.) |
| `map_informe` | `(source_kind, content) → [{ficha, linha, value, confidence}]` | Map Informe de Rendimentos to declaration fields. **V1 hard-capped** to the specific sources detected in the user's own 2025 `.DBK`; auto-detected, listed below. |
| `compute_tax` | `(DeclarationJSON, modelo='completa'\|'simplificada') → {imposto_devido, restituir_pagar, breakdown}` | Advisory tax calc from decompiled `irpf-negocio-calculo.jar`. **Always returns a disclaimer.** |

### Skills (Claude Code) and Agents (Codex)

Same five user-facing wrappers in both ecosystems:

- **`irpf-decode`** — "decode my .DBK and summarize it"
- **`irpf-ask`** — "answer my IRPF question authoritatively" (responses MUST cite source: pergunta # / Leiaute § / Ajuda page)
- **`irpf-fill`** — guided workflow: list source documents → `map_informe` → present mappings → user confirms → emit draft JSON
- **`irpf-diff`** — "compare this year vs last year, flag anomalies"
- **`irpf-audit`** — runs `sanity_check` on a draft, reports findings

### Knowledge extraction pipeline (runs once per tax year)

Outputs all land in `packages/irpf_knowledge/src/irpf_knowledge/data/2026/`.

1. **JAR decompilation** → `jar_field_map_2026.json`
   - Tool: [CFR](https://www.benf.org/other/cfr/) (or Procyon as backup)
   - Targets (priority): `irpf-importacao-exportacao.jar` (DBK reader/writer — the goldmine), `irpf-negocio-declaracao.jar` (record layouts), `irpf-negocio-calculo.jar` (tax math), `irpf-gui-declaracao.jar` (field labels)
   - Extract: field-ID constants, validator regexes, length constants, parser/writer methods (translated to Python, not invoked)

2. **`AjudaIRPF.pdf`** → `ajuda_2026.md` via **Docling**
   - Tables preserved as Markdown tables
   - Section headings become anchors, indexed for `explain_field` lookups

3. **Perguntas e Respostas IRPF 2026** (RFB PDF) → `perguntas_2026.md` (Docling) → post-processor → `perguntas_2026.jsonl`
   - One record per Q&A: `{num, titulo, pergunta, resposta, ficha_refs[]}`
   - Embedded into a small local FAISS / sqlite-vec index for semantic search

4. **Leiaute do IRPF 2026** (RFB Developer Portal PDF) → `leiaute_2026.md` (Docling) → post-processor → `leiaute_2026.json`
   - Authoritative record-offset spec
   - **Cross-validation gate**: JAR-derived offsets MUST equal Leiaute offsets for every record type. Discrepancy = bug to resolve before commit.

---

## Critical files to be created

(All new — the repo directory is empty.)

- `pyproject.toml`, `uv.lock`
- `packages/irpf_core/src/irpf_core/{schema.py, parser.py, encoder.py, validators.py, calc.py}`
- `packages/irpf_knowledge/src/irpf_knowledge/{__init__.py, loader.py}` + `data/2026/*`
- `packages/irpf_mcp/src/irpf_mcp/{server.py, tools.py}`
- `extractors/{decompile_jars.py, parse_ajuda_pdf.py, parse_perguntas.py, parse_leiaute.py}`
- `integrations/claude_skills/*/SKILL.md` (×5)
- `integrations/codex_agents/AGENTS.md`
- `fixtures/synthetic-2026.dbk`
- `tools/redact.py`
- `NOTICE.md` (reverse-engineering justification), `.gitignore`, `README.md`

## Reused tooling / libraries (no new code to write)

- **Docling** — PDF → Markdown with table extraction (extractor-only dep)
- **CFR** (Java) — JAR decompilation (called via subprocess in `extractors/decompile_jars.py`)
- **MCP Python SDK** (`mcp`) — server scaffolding
- **uv** — workspace + lockfile
- **pytest** — tests
- **sqlite-vec** or **faiss-cpu** — semantic index for `lookup_pergunta` (decide during implementation; sqlite-vec preferred — no native heavyweight dep)
- **pydantic** — `DeclarationJSON` schema typing

---

## Implementation phases

Each phase ends with a committable state and a verification step.

### Phase 0 — Repo scaffolding
- `git init` in `~/irpf-mentor/`
- `uv init` workspace; create the three packages (`irpf_core`, `irpf_knowledge`, `irpf_mcp`) as members
- `.gitignore` blocking `*.DBK`, `*.DEC`, `*.REC` outside `fixtures/`, plus a regex check for 11-digit CPF patterns in pre-commit
- `NOTICE.md` and `README.md` skeletons
- Copy this design to `docs/superpowers/specs/2026-05-26-irpf-mentor-design.md`
- **Verify:** `uv sync` succeeds; `pytest` runs (zero tests yet)

### Phase 1 — `.DBK` parser/encoder + synthetic fixture
- Manual analysis of the first ~200 bytes of the user's real `.DBK` (header, identificacao record) to write a first-pass schema for IDENTIFICACAO
- Write `tools/redact.py`: takes a real `.DBK`, replaces CPF/CNPJ/name/address/values with fake-but-format-valid data, outputs `fixtures/synthetic-2026.dbk`
- User runs `redact.py` against their real file **locally**; commits only the synthetic output
- Implement `irpf_core.parser.decode()` and `encoder.encode()` for IDENTIFICACAO + DEPENDENTES + BENS records (first three record types)
- **Verify:** `decode(synthetic) → encode → decode == identity`; `pytest` passes

### Phase 2 — JAR decompilation + knowledge extraction
- `extractors/decompile_jars.py` — calls CFR on each `lib-modulos/*.jar`, writes Java source to a gitignored `extractors/_decompiled/` workspace
- Parse decompiled sources for: field-ID string constants, validator regex patterns, record-layout class structures
- Output: `jar_field_map_2026.json`
- `extractors/parse_ajuda_pdf.py`, `parse_perguntas.py`, `parse_leiaute.py` — Docling pipelines
- **Cross-validation gate** in `parse_leiaute.py`: assert JAR offsets ≡ Leiaute offsets; raise on mismatch
- **Verify:** Extractors produce all four artifacts; round-trip on the synthetic fixture still holds after switching from manual schema to JAR-derived schema; tests pass

### Phase 3 — Complete record-type coverage
- Extend `irpf_core` to all remaining record types: rendimentos_pj, rendimentos_pf, rendimentos_isentos, dividas, pagamentos, doacoes, renda_variavel, carne_leao, atividade_rural
- Validators per field (from `jar_field_map_2026.json`)
- **Verify:** Synthetic fixture round-trips through every record type; manual gate — synthetic fixture imports cleanly into the actual IRPF2026 app (user runs the app once)

### Phase 4 — MCP server: read-only tools
- `irpf_mcp.server` with: `decode_declaration`, `explain_field`, `lookup_pergunta`, `validate_field`, `sanity_check`, `diff_declarations`
- Semantic index built lazily on first `lookup_pergunta` call
- **Verify:** MCP integration test — launch server, call each tool against `fixtures/synthetic-2026.dbk`, assertions on shape

### Phase 5 — Write-side & calc
- `encode_declaration`, `compute_tax` (with mandatory disclaimer string in every response)
- **Verify:** Encoded output still imports into IRPF2026; computed tax compared to the app's display for at least one synthetic scenario

### Phase 6 — `map_informe` (scope-capped)
- Auto-detect the user's actual informe sources from their 2025 `.DBK` (which CNPJs appear in rendimentos_pj). List them in `docs/supported_sources_2026.md`.
- Implement parsers for **only those sources**. Each is a small module under `packages/irpf_core/src/irpf_core/informes/<source>.py` implementing a common `parse(content) → list[FieldMapping]` interface.
- **Verify:** For each supported source, given a redacted sample file, produces correct ficha/linha mappings

### Phase 7 — Skills & agents
- Write the five Claude Code skills under `integrations/claude_skills/`
- Mirror as Codex agents under `integrations/codex_agents/`
- Each must include: when to invoke, which MCP tools to call in what order, citation requirements (irpf-ask), confirmation gates (irpf-fill before emitting)
- **Verify:** Manual end-to-end — install MCP locally, invoke each skill in a fresh Claude Code session, confirm the workflow produces the expected outcome

### Phase 8 — Hardening & docs
- Pre-commit hook scanning for CPF patterns outside `fixtures/`
- README with: quickstart, MCP install instructions, skill install instructions, "how to bump for next tax year" runbook
- `NOTICE.md` finalized

---

## Verification (end-to-end)

After Phase 8, all of these must pass:

1. **`uv run pytest`** — green across all packages
2. **Round-trip:** `decode(synthetic-2026.dbk) → encode → decode` is identity
3. **Real-app gate:** synthetic fixture imports into IRPF2026 without errors (manual, one-time per phase)
4. **MCP smoke test:** `uv run irpf-mcp` boots, each tool callable, returns shaped responses against the fixture
5. **Claude Code skills:** `irpf-decode` on the synthetic fixture produces a coherent summary; `irpf-ask "como declarar previdência privada PGBL?"` returns an answer that cites a specific pergunta number
6. **Codex agents:** same five workflows succeed in a Codex session
7. **Privacy gate:** `grep -rE '[0-9]{11}' --include='*.dbk' --include='*.DBK' .` returns zero matches outside `fixtures/` (and the fixture CPF is the known synthetic one)

---

## Open risks (documented, mitigated)

1. **Decompilation of RFB JARs** — done for interop with the user's own declaration, no redistribution of JARs or decompiled source (only derived field maps). `NOTICE.md` states this explicitly.
2. **`map_informe` scope** — V1 hard-capped to sources present in the user's actual 2025 `.DBK`. Everything else is "contributions welcome."
3. **Yearly drift** — RFB changes layouts annually. `data/<year>/` versioning makes the maintenance cost a yearly re-run of extractors, not a rewrite.
4. **PDF parsing fragility** — Docling outputs are snapshot-tested; any RFB PDF restructure surfaces immediately.
5. **Tax-calc accuracy** — `compute_tax` is advisory only; every response carries a "verify in the official app before submitting" disclaimer.
