"""Convert RFB 'Perguntas e Respostas IRPF 2026' PDF to Markdown + JSONL.

The Receita Federal publishes the authoritative ~745-question Q&A guide as a
~4.6 MB PDF on gov.br. This script:

1. Runs Docling on the PDF to produce structured Markdown (tables preserved).
2. Heuristically splits the Markdown into individual Q&A records using the
   numeric-prefix pattern (e.g. "001 —", "002 —") common to RFB Perguntas.
3. Writes both:
   - data/2026/perguntas_2026.md (the full Markdown, for human reading and
     LLM full-document retrieval)
   - data/2026/perguntas_2026.jsonl (one JSON object per Q&A, indexable for
     the MCP `lookup_pergunta` tool)

Run:

    uv run --group extractors python extractors/parse_perguntas.py \\
        --in  extractors/_pdfs/perguntas_irpf_2026.pdf \\
        --out-md   packages/irpf_knowledge/src/irpf_knowledge/data/2026/perguntas_2026.md \\
        --out-jsonl packages/irpf_knowledge/src/irpf_knowledge/data/2026/perguntas_2026.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

QA_HEADING_PATTERN = re.compile(
    r"^(?P<full>(?:#{1,6}\s+)?\**\s*(?P<num>\d{1,4})\s*[—\-–]\s*(?P<title>.+?))\**\s*$",
    re.MULTILINE,
)
"""Matches Q&A headings like '001 — Título da pergunta?' with optional
leading '#'/'##' Markdown heading prefix and optional surrounding `**`.

Captures `num` (the question number, normalized via int()) and `title`.
"""


def run_docling(input_pdf: Path) -> str:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = True

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)},
    )
    print(f"Converting {input_pdf} via Docling…", flush=True)
    result = converter.convert(str(input_pdf))
    return result.document.export_to_markdown()


def split_into_qa(markdown: str) -> list[dict]:
    """Split the document into Q&A records using numeric-prefix headings."""
    matches = list(QA_HEADING_PATTERN.finditer(markdown))
    if not matches:
        return []

    qa: list[dict] = []
    seen_numbers: set[int] = set()
    for i, m in enumerate(matches):
        num = int(m.group("num"))
        if num in seen_numbers:
            continue
        if not 1 <= num <= 1500:
            continue
        seen_numbers.add(num)

        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[body_start:body_end].strip()

        qa.append({
            "num": num,
            "titulo": m.group("title").strip(),
            "resposta": body,
        })
    qa.sort(key=lambda r: r["num"])
    return qa


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="input", required=True, type=Path)
    parser.add_argument("--out-md", dest="output_md", required=True, type=Path)
    parser.add_argument("--out-jsonl", dest="output_jsonl", required=True, type=Path)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input PDF not found: {args.input}", file=sys.stderr)
        return 2

    md = run_docling(args.input)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(md, encoding="utf-8")
    print(f"Wrote {args.output_md} — {len(md):,} chars", flush=True)

    qa = split_into_qa(md)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for rec in qa:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {args.output_jsonl} — {len(qa)} Q&A records", flush=True)

    if len(qa) < 100:
        print(f"WARNING: only {len(qa)} Q&A records extracted — heading "
              f"pattern may need adjustment for this year's PDF layout.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
