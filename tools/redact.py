"""Convert a real IRPF .DBK / .DEC into a fully de-identified synthetic fixture.

Run locally against your real declaration; commit only the output. The output
is safe to publish: every identifying field is replaced with a synthetic value
of identical byte width, so the file still round-trips and parses, but contains
none of your personal data.

Usage:

    uv run python tools/redact.py \\
        --in  ~/ProgramasRFB/IRPF2026/<your-declaration>.DBK \\
        --out fixtures/synthetic-2026.dbk

Scrub policy (leiaute-driven, applied to every record):

- Identity:   NR_CPF / CPF_* , NM_NOME, NM_EMAIL, DT_NASCIM, NR_TITELEITOR,
              NR_NITPISPASEP, NR_RENAVA*
- Address:    NM_LOGRA, NR_NUMERO, NM_COMPLEM, NM_BAIRRO, NR_CEP,
              CD_MUNICIP, NM_MUNICIP   (SG_UF kept — not identifying)
- Banking:    NR_BANCO, NR_AGENCIA, NR_CONTA, NR_DV*
- 3rd parties: NM_BENEF, NM_FONTE, NM_PAGAD*, source NM_NOME, *CNPJ* / *CPFCNPJ*
- Free text:  TX_* (asset descriptions etc. — can embed account numbers)

Monetary VR_* values and generic classifier codes (CD_OCUP, CD_PAIS, CD_BEM,
CD_NATUR) are kept — they make the fixture realistic test data and are not
personally identifying once names/CPF/address/accounts are gone.

What it does NOT guarantee: that the output imports into the official IRPF
program (trailer totals / NR_HASH are not recomputed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from irpf_core import decode_bytes, encode, field_str
from irpf_core.accessors import field_spec

SYNTHETIC_CPF = "00000000191"          # passes the modulo-11 check
SYNTHETIC_CNPJ = "11222333000181"      # a valid synthetic CNPJ

# Substring keywords on the field NAME → field carries PII and must be scrubbed.
# (All NM_* name fields and TX_* free-text fields are scrubbed unconditionally;
# these keywords catch numeric identifiers and a few odd names.)
_PII_KEYWORDS = (
    "CPF", "CNPJ", "EMAIL", "LOGRA", "BAIRRO", "COMPLEM", "CEP",
    "TELEFONE", "CELULAR", "DDD", "TITELEITOR", "NITPISPASEP", "RENAVA",
    "NR_CONTA", "NR_AGENCIA", "NR_DV", "NR_BANCO", "PAGADOR", "CONTRIBUINTE",
    "CD_MUNICIP", "NR_NUMERO", "DT_NASCIM", "MATRIC_IMOV", "NR_IPTU", "NR_CIB",
)
_PII_PREFIXES = ("NM_", "TX_")


def _is_pii(name: str) -> bool:
    return name.startswith(_PII_PREFIXES) or any(k in name for k in _PII_KEYWORDS)


def _synthetic(name: str, tipo: str, width: int) -> bytes:
    """Produce a width-exact synthetic value appropriate to the field."""
    if "DT_NASCIM" in name and width == 8:
        return b"01011990"
    if tipo == "N" or (tipo in ("C",) and any(k in name for k in ("CPF", "CNPJ"))):
        # Numeric-ish identifier.
        if "CNPJ" in name and width >= 14:
            digits = SYNTHETIC_CNPJ
        elif "CPF" in name and width >= 11:
            digits = SYNTHETIC_CPF
        else:
            digits = ""  # zero-fill below
        return digits.rjust(width, "0")[:width].encode("ascii")

    # Alpha / char free text — pick a readable synthetic by category.
    if "EMAIL" in name:
        base = "teste@exemplo.com.br"
    elif name in ("NM_NOME", "NM_CONTRIBUINTE"):
        base = "JOAO DA SILVA SANTOS DE TESTE"
    elif any(k in name for k in ("BENEF", "FONTE", "PAGAD")):
        base = "INSTITUICAO SINTETICA DE TESTE LTDA"
    elif "LOGRA" in name:
        base = "RUA DE TESTE"
    elif "BAIRRO" in name:
        base = "BAIRRO TESTE"
    elif "MUNICIP" in name:
        base = "CIDADE TESTE"
    elif name.startswith("TX_"):
        base = "DESCRICAO SINTETICA PARA TESTE"
    elif "COMPLEM" in name:
        base = ""
    else:
        base = "TESTE"
    return base.ljust(width)[:width].encode("ascii")


def redact(input_path: Path, output_path: Path) -> None:
    data = input_path.read_bytes()
    decl = decode_bytes(data)

    scrubbed_fields = 0
    for rec in decl.records:
        if not hasattr(rec, "fields"):
            continue
        for fname in list(rec.fields):
            base_name = fname.split("__", 1)[0]  # undo FILLER-style disambiguation
            if not _is_pii(base_name):
                continue
            current = rec.fields[fname]
            if not current.strip():  # already blank — leave it
                continue
            try:
                spec = field_spec(rec, base_name)
                tipo = spec["tipo"]
            except KeyError:
                tipo = "A"
            rec.fields[fname] = _synthetic(base_name, tipo, len(current))
            scrubbed_fields += 1

    final_bytes = encode(decl)
    if len(final_bytes) != len(data):
        raise RuntimeError(
            f"Length changed during redaction: {len(data)} -> {len(final_bytes)}."
        )

    # Hard guarantees: none of the real identifying tokens survive.
    real = decode_bytes(data)
    for token in (
        field_str(real.identificacao, "NR_CPF"),
        field_str(real.identificacao, "NM_NOME"),
        field_str(real.identificacao, "NM_EMAIL"),
        field_str(real.identificacao, "NR_CEP"),
        field_str(real.identificacao, "NR_CELULAR"),
    ):
        if token and token.encode("ascii") in final_bytes:
            raise RuntimeError(f"Real PII token still present after redaction: {token!r}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(final_bytes)
    print(f"Redacted {scrubbed_fields} fields → {output_path} ({len(final_bytes)} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="input", required=True, type=Path)
    parser.add_argument("--out", dest="output", required=True, type=Path)
    args = parser.parse_args()
    if not args.input.exists():
        print(f"Input file does not exist: {args.input}", file=sys.stderr)
        return 2
    redact(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
