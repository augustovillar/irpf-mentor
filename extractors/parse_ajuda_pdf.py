"""Convert the bundled AjudaIRPF.pdf to Markdown using Docling.

The official IRPF 2026 installer ships a 4.5 MB help PDF at
~/ProgramasRFB/IRPF2026/help/AjudaIRPF.pdf covering every field of every
form. Docling preserves tables (limites de dedução, faixas IRPF, código de
bens, países, ocupações principais) which pdfplumber would mangle.

This script is single-shot per tax year. It does NOT need OCR — the PDF is
digital-native. Disable it for ~10x speedup.

Run:

    uv run --group extractors python extractors/parse_ajuda_pdf.py \\
        --in  ~/ProgramasRFB/IRPF2026/help/AjudaIRPF.pdf \\
        --out packages/irpf_knowledge/src/irpf_knowledge/data/2026/ajuda_2026.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def convert(input_path: Path, output_path: Path) -> None:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = True

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)},
    )
    print(f"Converting {input_path} (may take several minutes — table structure on, OCR off)…")
    result = converter.convert(str(input_path))

    md = result.document.export_to_markdown()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    print(f"Wrote {output_path} — {len(md):,} chars, "
          f"{md.count(chr(10)):,} lines")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="input", required=True, type=Path)
    parser.add_argument("--out", dest="output", required=True, type=Path)
    args = parser.parse_args()
    if not args.input.exists():
        print(f"Input PDF not found: {args.input}", file=sys.stderr)
        return 2
    convert(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
