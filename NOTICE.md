# Notice

## Reverse engineering for interoperability

This project analyzes the official Receita Federal *Programa Gerador da Declaração IRPF 2026* (PGD IRPF) for the sole purpose of **interoperating with the file formats** (`.DBK`, `.DEC`, `.REC`) used by Brazilian taxpayers to manage their own income-tax declarations.

We:

- **Do not** redistribute the PGD IRPF binaries, JAR files, or the help PDF bundled with the official installer.
- **Do not** commit decompiled Java source to this repository.
- **Do** commit only *derived data*: field-offset tables, validator rules, and label strings, expressed in our own JSON/Markdown form.
- **Do** treat the official Receita Federal *Leiaute do IRPF*, *Perguntas e Respostas*, and the bundled `AjudaIRPF.pdf` as the authoritative cross-check for any extracted information.

Where Brazilian copyright law applies, this analysis is intended to fall within the interoperability allowances of Lei nº 9.609/1998 (Lei do Software). Where other jurisdictions' law applies, this work is intended to constitute fair use / fair dealing for the purpose of interoperability and personal tax compliance.

## Data provenance

Some committed data files are derived from official Receita Federal publications, reproduced here for interoperability and educational reference:

- `packages/irpf_knowledge/src/irpf_knowledge/data/2026/ajuda_2026.md` — converted to Markdown from the `AjudaIRPF` help bundled with the official PGD IRPF 2026, via the extractors pipeline.
- `packages/irpf_knowledge/src/irpf_knowledge/data/2026/perguntas_2026.{md,jsonl}` — structured from the Receita Federal *Perguntas e Respostas IRPF 2026* publication.
- `packages/irpf_knowledge/src/irpf_knowledge/data/2026/leiaute_2026.json` — derived field-offset facts (record layout) extracted from the official program; expressed in our own JSON form.

These are public Brazilian government materials, reproduced unmodified in substance for the interoperability purpose described above. Receita Federal remains the authoritative source; consult the official program and publications before relying on any value here.

## Disclaimer

Outputs of this project — including tax calculations, validation results, and field mappings — are **advisory**. The official IRPF 2026 program is the only authoritative source for a valid declaration submitted to Receita Federal. Always import any draft into the official app and verify before transmitting.

## Trademarks

*Imposto de Renda*, *Receita Federal*, *IRPF*, and *PGD IRPF* are marks of the Brazilian federal government. This project is not affiliated with, endorsed by, or sponsored by Receita Federal do Brasil.
