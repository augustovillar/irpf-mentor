# irpf-mentor — Improvement Roadmap

Status at time of writing: all 9 build phases done, 44 tests, 9+2 MCP tools,
local-only on `main`. This roadmap captures every improvement idea, grouped by
theme, with **value**, **effort**, and **blockers**. Tiers: **P0** (high
value / unblocked / do next), **P1** (valuable, some cost or decision), **P2**
(big or speculative).

---

## A. Knowledge & retrieval quality

### A1 — Wire AjudaIRPF into `explain` · P0 · small · unblocked
`explain` currently returns only the leiaute spec (type/size/offset). We
already shipped `ajuda_2026.md` (895 KB) but nothing consumes it. Index the
Ajuda by ficha/section and have `explain(record_type, field?)` attach the
official human-readable help text. Biggest quality win per hour.

### A2 — Extract the code tables · P0 · small · unblocked
`irpf.jar` also bundles `tipoBensAR.xml`, `paises_gcap.xml`, `ufs.xml`,
`tipoLogradouro.xml`, `racaCor.xml`, `moedas.xml`, `tipoConta.xml`, etc. Extract
them into `irpf_knowledge` as lookup tables so we can translate codes
(CD_BEM=02 → "…", CD_PAIS=105 → "Brasil", CD_MUNICIP → city) in `decode`,
`explain`, and validation.

### A3 — Semantic search for `lookup_perguntas` · P1 · medium · decision needed
Keyword search misses vocabulary mismatches ("carro" vs "veículo"). Options:
(a) lightweight: PT stemming (RSLP) + a curated synonym map — no heavy deps;
(b) embeddings: a small multilingual model + sqlite-vec — best quality but adds
weight to the MCP runtime (violates the "lean MCP" invariant — deliberate
call). Recommend starting with (a), measuring, then (b) if needed.

### A4 — Recover the 11 missing Perguntas · P1 · small · unblocked
Coverage is 734/745. The misses cluster around layout variations (28-31,
107-108, …). Refine the splitter regex in `parse_perguntas.py` against those
pages — no need to re-run Docling, just re-split the committed Markdown.

### A5 — Link Perguntas ↔ fichas · P1 · medium · unblocked
Tag each Q&A with the records/fields it concerns (`ficha_refs`) so `explain`
can surface "related questions" and `irpf-ask` can cite the exact ficha.

### A6 — Extract validator logic from JARs · P1 · medium · unblocked
The decompiled `irpf-negocio-*` JARs contain the real field validators
(CPF/CNPJ checksum, date sanity, cross-field rules). Port the high-value ones
into `validate` so it catches semantically-invalid (not just wrong-typed)
values.

---

## B. Parser / encoder correctness

### B1 — Real-app import gate · P0 · trivial · needs user (GUI)
Import `fixtures/synthetic-2026.dbk` into IRPF 2026 ("Importar Declaração") and
confirm it loads clean. Ground-truth proof the encoder is byte-correct. One-time
manual click-through.

### B2 — Valid-on-export encode · P1 · medium-hard · unblocked
Edited `.DBK`s currently need re-finalizing by the official program because we
don't recompute the trailer record counts or the `NR_HASH` (CRC32 — the
decompiled code references `serpro.hash.Crc32`). Reverse-engineer the hash input
and trailer math so `encode` emits directly-importable files. Unlocks true
write workflows.

### B3 — Friendly typed models for common records · P1 · medium · unblocked
On top of generic `TypedRecord`, add thin typed views for the records people
actually touch (Bem, Pagamento, Dependente, RendimentoPJ) with named
properties + money-as-Decimal, so callers don't juggle raw field dicts.

### B4 — Handle .DEC / .REC / online-header variants · P2 · medium · unblocked
Explicitly support the transmitted `.DEC`, receipt `.REC`, and the SR-online
header variant (`REG_HEADER_SR_ONLINE`) the leiaute already describes.

### B5 — Multi-year scaffolding · P2 · medium · partial blocker
Thread `tax_year` everywhere it's currently defaulted to 2026; add prior/next
year leiautes as they become available. Enables historical diffs across years.

---

## C. Tax logic

### C1 — Tax recomputation engine · P2 · large · unblocked (risky)
Port the calc from `irpf-negocio-calculo.jar`: faixas progressivas, deductions,
simplified vs complete. Advisory only, heavily tested. Large and error-prone —
the current `tax` tool (reads stored values) is the safe interim.

### C2 — What-if simulation · P2 · medium · depends on C1
Change a value → recompute the tax delta. The headline "should I do X?" feature.

### C3 — Model comparison · P1-after-C1 · small · depends on C1
Simplified vs complete: compute both, recommend the lower tax. (The program does
this, but doing it ourselves enables it during drafting.)

---

## D. Fill-from-documents (informe)

### D1 — First concrete informe parser · P0-when-unblocked · medium · needs sample
Framework is ready. One redacted Nubank/BancoSeguro *Informe de Rendimentos*
lets me build + test the first real parser, scoped to the user's own sources.

### D2 — PDF/XLSX informe ingestion · P1 · medium · needs samples
Many informes are PDF/XLSX. Reuse Docling (PDF) + openpyxl (XLSX) in the
informe layer so `map_document` accepts files, not just pasted text.

### D3 — Pré-preenchida (.xml) import · P1 · medium · unblocked-ish
The program supports a pre-filled declaration; `ImportadorPrePreenchida.java`
exists. Parsing the pré-preenchida XML would auto-populate large chunks.

### D4 — GCAP / Carnê-Leão feeds · P2 · medium · needs samples
Other PGD programs (capital gains, monthly book) feed IRPF — support their
exports.

---

## E. Diff / audit depth

### E1 — Richer sanity rules · P0 · small · unblocked
Add: CPF/CNPJ checksum validity, dependente CPF valid, bem with value but no
acquisition date, sum-of-records vs trailer totals, duplicate dependentes.
Cheap, high trust.

### E2 — Item-level semantic diff · P1 · medium · unblocked
Beyond counts: match bens/pagamentos across years by key and report
money-deltas (%), appreciation, new/sold assets as a narrative.

---

## F. Distribution / DX / ops

### F1 — GitHub Actions CI · P0 · small · unblocked
Run `pytest` + `ruff` + `check_no_pii.py` on every push/PR. Cheap safety net.

### F2 — History scrub before publish · P0-before-push · small · unblocked
The real CPF still lives in older commits' file trees. Before any push, purge
with `git filter-repo` (or squash to a clean root commit). Required gate for
going public.

### F3 — uvx-runnable / PyPI · P1 · small · unblocked
Make `uvx irpf-mentor-mcp` work without cloning; publish `irpf-core`/`irpf-mcp`.

### F4 — Standalone CLI · P2 · small · unblocked
`irpf-mentor decode/explain/ask` for non-MCP terminal use.

---

## G. Safety / privacy

### G1 — Strengthen `redact.py` · P0 · medium · unblocked
Today it scrubs CPF + name + DOB only. Extend to CNPJs, address, CEP, phone,
bank account numbers, and bem free-text descriptions so the fixture (and any
shared sample) is fully de-identified.

### G2 — Expand the PII scanner · P1 · small · unblocked
`check_no_pii.py` catches CPF-shaped tokens; add CEP, full-name heuristics, and
bank-account patterns.

### G3 — Privacy mode in `decode` · P2 · small · unblocked
Option to mask PII fields in tool output by default (show `***`-masked CPF
unless explicitly requested).

---

## H. UX / output

### H1 — Human-readable declaration report · P1 · small · unblocked
A `report(path)` tool that renders the whole declaration as a clean Markdown
summary (identificação, rendimentos, bens table with R$, pagamentos, totals).

### H2 — Consistent PT-BR + R$ formatting · P1 · small · unblocked
Money helper (R$ 1.234,56) and PT-BR phrasing across all tool outputs.

---

## Recommended near-term sequence

1. **A1** (Ajuda → explain) + **A2** (code tables) — biggest knowledge wins.
2. **E1** (richer sanity) + **G1** (stronger redaction) — trust & safety.
3. **F1** (CI) + **B1** (import gate) — verification.
4. **A3** (semantic search) — after deciding the dependency tradeoff.
5. **D1** (first informe parser) — as soon as a sample lands.
6. **B2** (valid-on-export) then **C1** (tax engine) — the heavy, high-value
   write/compute features.
