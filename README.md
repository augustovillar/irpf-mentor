# irpf-mentor

Toolkit for the Brazilian *Imposto de Renda Pessoa Física* (IRPF 2026)
declaration. An **MCP server** exposes decoding + authoritative knowledge to
LLMs; **Claude Code skills** and **Codex agents** wrap it into workflows.

Tax year: **IRPF 2026** (ano-base 2025).

## What it does

- **Decode** your `.DBK`/`.DEC` into structured data (all 86 record types,
  parsed against the layout extracted from the official `irpf.jar`).
- **Answer IRPF questions** authoritatively from the official RFB *Perguntas e
  Respostas* (734 Q&As) and *AjudaIRPF* — with citations, no hallucination.
- **Validate / audit** a declaration (field rules, CPF consistency, …).
- **Diff** two declarations (this year vs last year).
- **Edit & re-emit** a `.DBK` for import back into the official program.

## Layout

```
packages/irpf_core/        # parser, encoder, schema, validators, accessors
packages/irpf_knowledge/   # committed extracted knowledge per tax year
packages/irpf_mcp/         # MCP server (11 tools)
extractors/                # one-shot build scripts: JAR layout + Docling PDFs
integrations/claude_skills # 5 Claude Code skills
integrations/codex_agents  # Codex AGENTS.md mirror
fixtures/                  # synthetic, redacted test data only
tools/                     # redact.py, check_no_pii.py
```

## Quickstart

```bash
uv sync
uv run pytest          # 44 tests
```

To regenerate the synthetic fixture from your own (gitignored) declaration:

```bash
uv run python tools/redact.py \
    --in  ~/ProgramasRFB/IRPF2026/<your-file>.DBK \
    --out fixtures/synthetic-2026.dbk
```

## Use it from Claude Code

No clone needed — register the MCP server straight from GitHub (`uv` builds and
caches it on first run):

```bash
claude mcp add irpf-mentor -- uvx --from git+https://github.com/augustovillar/irpf-mentor irpf-mcp
```

Then install the five skills:

```bash
git clone https://github.com/augustovillar/irpf-mentor && cd irpf-mentor
./scripts/install_skills.sh          # copies into ~/.claude/skills/  (--link to symlink)
```

Ask things like *"decode ~/ProgramasRFB/IRPF2026/transmitidas/…​.DEC"* or *"como
declaro previdência privada PGBL?"*.

> Developing locally? Point the server at your checkout instead:
> `claude mcp add irpf-mentor -- uv run --directory /ABSOLUTE/PATH/TO/irpf-mentor irpf-mcp`

## Use it from Codex

Add to `~/.codex/config.toml` (no clone needed):

```toml
[mcp_servers.irpf-mentor]
command = "uvx"
args = ["--from", "git+https://github.com/augustovillar/irpf-mentor", "irpf-mcp"]
```

See `integrations/codex_agents/AGENTS.md` for the workflow instructions.

> Developing locally? Use `command = "uv"` with
> `args = ["run", "--directory", "/ABSOLUTE/PATH/TO/irpf-mentor", "irpf-mcp"]`.

## MCP tools

| Tool | Purpose |
|---|---|
| `decode(path)` | Parse a `.DBK`/`.DEC` → structured JSON |
| `explain(record_type, field?)` | Authoritative leiaute spec for a record/field |
| `list_records()` | All 86 record types |
| `lookup_perguntas(query, top_k)` | Search the 734 RFB Q&As (accent-aware) |
| `validate(record_type, field, value)` | Field-level validation |
| `sanity(path)` | Cross-field consistency findings |
| `diff(path_old, path_new)` | Compare two declarations |
| `encode(declaration, output_path)` | Re-emit an edited `.DBK` |
| `tax(path)` | Read the program-computed tax figures (advisory) |
| `sources(path)` | Detect candidate source documents (informes) for a declaration |
| `map_document(content, source_kind?)` | Map an informe's content onto declaration fields |

## Privacy backstop

Real `.DBK`/`.DEC`/`.REC` files are PII and are blocked by `.gitignore`
outside `fixtures/`. A pre-commit hook adds defense in depth:

```bash
# Option A: the pre-commit framework
pip install pre-commit && pre-commit install

# Option B: a native git hook
ln -sf ../../tools/check_no_pii.py .git/hooks/pre-commit  # or wrap in a shell hook
```

`tools/check_no_pii.py` blocks staged declaration files outside `fixtures/`
and flags stray CPF-shaped tokens in any staged file.

## Bumping for the next tax year (2027)

1. Install the new official IRPF program (`~/ProgramasRFB/IRPF2027/`).
2. Re-run the extractors against the new jar/PDFs, writing to
   `packages/irpf_knowledge/src/irpf_knowledge/data/2027/`:
   ```bash
   uv run python extractors/extract_layout.py    --irpf-jar ~/ProgramasRFB/IRPF2027/irpf.jar --out .../data/2027/leiaute_2027.json
   uv run --group extractors python extractors/parse_ajuda_pdf.py --in ~/ProgramasRFB/IRPF2027/help/AjudaIRPF.pdf --out .../data/2027/ajuda_2027.md
   uv run --group extractors python extractors/parse_perguntas.py --in <perguntas-2027.pdf> --out-md .../perguntas_2027.md --out-jsonl .../perguntas_2027.jsonl
   ```
3. Add `2027` to `SUPPORTED_TAX_YEARS` in `irpf_knowledge/loader.py` and
   thread the `tax_year` argument through where it's currently defaulted.
4. Run the cross-validation: every record length in a real 2027 file must
   match the new leiaute's `tamanho_total`.

## License

See [LICENSE](LICENSE). This is **not** open source: personal, non-commercial
use and modification are permitted, but commercial use and redistribution are
not. RFB-derived data has its own provenance — see [NOTICE.md](NOTICE.md).

## Notice

See [NOTICE.md](NOTICE.md) — reverse-engineering for interoperability; outputs
are advisory; the official program is authoritative before transmitting.
