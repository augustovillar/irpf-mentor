"""Extract the IRPF 2026 record layout from the official irpf.jar.

The IRPF 2026 program bundles its own machine-readable record layout in
`mapeamentoTxt.xml` inside irpf.jar. Every record type (REG_HEADER, REG_IDENTIFICACAO,
REG_PAGAMENTO, REG_BEM, …) is described with each field's name, type
(C=char/string, A=alpha, N=numeric, D=date, I=indicator), size in chars,
decimals (for numerics), and a human-readable description.

This script reads that XML and emits a much-smaller, version-controlled JSON
artifact suitable for shipping inside the `irpf_knowledge` package. The JSON
adds computed `offset` (byte position) for each field, derived by summing
preceding `tamanho` values — matching the algorithm in
`RegistroTxt.adicionaCampo` in the decompiled SERPRO library.

The script does NOT redistribute irpf.jar or the XML — it reads them from the
user's local install and writes our derived JSON.

Run once per tax year (or whenever a new IRPF 2026 patch ships):

    uv run --group extractors python extractors/extract_layout.py \\
        --irpf-jar ~/ProgramasRFB/IRPF2026/irpf.jar \\
        --out packages/irpf_knowledge/src/irpf_knowledge/data/2026/leiaute_2026.json
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

TIPO_ARQUIVO = "ARQ_IRPF"
"""We extract only the IRPF declaration mapping; the same XML also contains
mappings for ARQ_GCAP (capital gains), ARQ_GCME (foreign currency capital
gains), and ARQ_PREPREENCHIDA (pre-filled declaration) which we ignore for V1."""


def extract_xml_from_jar(jar_path: Path, member: str = "mapeamentoTxt.xml") -> bytes:
    with zipfile.ZipFile(jar_path) as zf:
        return zf.read(member)


def parse_layout(xml_bytes: bytes) -> dict[str, Any]:
    """Return a dict keyed by record `Identificador` (e.g. 'IR', '16', '27', 'T9')."""
    root = ET.fromstring(xml_bytes)

    decl = None
    for d in root.findall("DeclaracaoTXT"):
        if d.attrib.get("TipoArquivo") == TIPO_ARQUIVO:
            decl = d
            break
    if decl is None:
        raise RuntimeError(
            f"No <DeclaracaoTXT TipoArquivo='{TIPO_ARQUIVO}'> in mapeamentoTxt.xml"
        )

    records: dict[str, Any] = {}
    for reg in decl.findall("Registro"):
        identificador = reg.attrib.get("Identificador", "").strip()
        if not identificador:
            continue
        if identificador in records:
            raise RuntimeError(
                f"Duplicate record identifier {identificador!r} in layout."
            )

        campos: list[dict[str, Any]] = []
        offset = 0
        for campo in reg.findall("Campo"):
            tipo = campo.attrib.get("Tipo", "").strip()
            tamanho_str = campo.attrib.get("Tamanho", "").strip()
            decimais_str = campo.attrib.get("Decimais", "").strip() or \
                campo.attrib.get("CasasDecimais", "").strip()
            if not tipo:
                raise RuntimeError(f"Field {campo.attrib} missing Tipo")

            if tipo == "I":
                tamanho = 1
            elif tipo == "D":
                tamanho = int(tamanho_str) if tamanho_str else 8
            else:
                if not tamanho_str:
                    raise RuntimeError(f"Field {campo.attrib} missing Tamanho")
                tamanho = int(tamanho_str)

            field = {
                "nome": campo.attrib.get("Nome", "").strip(),
                "tipo": tipo,
                "tamanho": tamanho,
                "offset": offset,
                "descricao": _normalize_ws(campo.attrib.get("Descricao", "")),
            }
            if decimais_str:
                field["decimais"] = int(decimais_str)
            if campo.attrib.get("Conteudo", "").strip():
                field["conteudo_estatico"] = campo.attrib["Conteudo"]
            if campo.attrib.get("ParticipaImportacao", "").strip() == "false":
                field["participa_importacao"] = False
            if campo.attrib.get("ParticipaGravacao", "").strip() == "false":
                field["participa_gravacao"] = False
            if campo.attrib.get("atributoObjetoNegocio", "").strip():
                field["atributo_negocio"] = campo.attrib["atributoObjetoNegocio"].strip()

            campos.append(field)
            offset += tamanho

        records[identificador] = {
            "nome": reg.attrib.get("Nome", "").strip(),
            "descricao": _normalize_ws(reg.attrib.get("Descricao", "")),
            "tamanho_total": offset,
            "campos": campos,
        }

    return records


def _normalize_ws(s: str) -> str:
    return " ".join(s.split()).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--irpf-jar", required=True, type=Path,
                        help="path to the official irpf.jar (usually ~/ProgramasRFB/IRPF2026/irpf.jar)")
    parser.add_argument("--out", required=True, type=Path,
                        help="path to write leiaute_2026.json")
    args = parser.parse_args()

    if not args.irpf_jar.exists():
        print(f"irpf.jar not found at {args.irpf_jar}", file=sys.stderr)
        return 2

    xml_bytes = extract_xml_from_jar(args.irpf_jar, "mapeamentoTxt.xml")
    records = parse_layout(xml_bytes)

    output = {
        "tax_year": 2026,
        "ano_base": 2025,
        "source": "mapeamentoTxt.xml (extracted from official IRPF 2026 irpf.jar)",
        "tipo_arquivo": TIPO_ARQUIVO,
        "records": records,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    rec_count = len(records)
    field_count = sum(len(r["campos"]) for r in records.values())
    print(f"Wrote {args.out} — {rec_count} record types, {field_count} fields total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
