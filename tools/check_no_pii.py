"""Pre-commit guard against committing IRPF PII.

Checks over the *staged* files:

1. Block any .DBK / .DEC / .REC staged outside `fixtures/` (the .gitignore
   already excludes these; this is defense in depth).

2. Scan staged files — INCLUDING the synthetic fixture — for identifying
   tokens, using patterns specific enough to avoid false positives in a
   fixed-width .dbk full of zero-padded numbers:
     - CPF: 11-digit run (not part of a longer number) or NNN.NNN.NNN-NN,
       excluding the known synthetic placeholder.
     - email: anything@domain, excluding example/exemplo domains.
     - CEP: NNNNN-NNN (punctuated only).
     - phone: (NN) NNNN-NNNN / (NN) NNNNN-NNNN (punctuated only).

For declaration files (.dbk/.dec/.rec) the bare 11-digit-run heuristic is
disabled: adjacent zero-padded numeric fields concatenate into 11-digit runs
that are not CPFs. Punctuated CPF, email, CEP and phone are still scanned.

Bare phone/CEP/account digit-runs are intentionally NOT scanned — in a .dbk
they collide with monetary values and codes. The redactor (tools/redact.py)
is the primary de-identification guarantee; this scanner is the backstop.

Data files derived from official RFB publications are allowlisted (they
legitimately contain example numbers).

Exit 0 = clean, 1 = problem (commit aborted).
"""

from __future__ import annotations

import re
import subprocess
import sys

SYNTHETIC_CPF_DIGITS = "00000000191"

ALLOWLIST_SUBSTRINGS = (
    "irpf_knowledge/src/irpf_knowledge/data/",
    "tools/check_no_pii.py",
    "tools/redact.py",
)

_BARE_CPF = re.compile(r"(?<!\d)\d{11}(?!\d)")
_PUNCT_CPF = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CEP = re.compile(r"(?<!\d)\d{5}-\d{3}(?!\d)")
_PHONE = re.compile(r"\(\d{2}\)\s?\d{4,5}-\d{4}")
_EXAMPLE_EMAIL = re.compile(r"@(?:exemplo|example)\.", re.IGNORECASE)


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def staged_blob(path: str) -> bytes:
    res = subprocess.run(["git", "show", f":{path}"], capture_output=True)
    return res.stdout if res.returncode == 0 else b""


def scan_text(text: str, *, bare_cpf: bool = True) -> list[str]:
    """Scan for identifying tokens.

    `bare_cpf=False` disables the unpunctuated 11-digit-run heuristic — used
    for fixed-width declaration files, where adjacent zero-padded numeric
    fields routinely concatenate into 11-digit runs that are not CPFs (e.g.
    IN_BEM_USUFRUTO + NR_CONTROLE). Punctuated CPF, email, CEP and phone are
    still scanned, and the redactor remains the primary guarantee for fixtures.
    """
    hits: list[str] = []

    cpfs = set(_PUNCT_CPF.findall(text))
    bare: set[str] = set()
    if bare_cpf:
        bare = {m for m in _BARE_CPF.findall(text) if m != SYNTHETIC_CPF_DIGITS}
        bare = {b for b in bare
                if not any(b == c.replace(".", "").replace("-", "") for c in cpfs)}
    for c in sorted(cpfs | bare):
        hits.append(f"CPF {c[:3]}***")

    for e in sorted(set(_EMAIL.findall(text))):
        if not _EXAMPLE_EMAIL.search(e):
            hits.append(f"email {e.split('@')[0][:3]}***@…")

    for c in sorted(set(_CEP.findall(text))):
        hits.append(f"CEP {c[:2]}***")

    for p in sorted(set(_PHONE.findall(text))):
        hits.append(f"phone {p[:4]}***")

    return hits


def main() -> int:
    problems: list[str] = []

    for path in staged_files():
        low = path.lower()

        if low.endswith((".dbk", ".dec", ".rec")) and not path.startswith("fixtures/"):
            problems.append(
                f"{path}: declaration file staged outside fixtures/ — "
                f"almost certainly real PII."
            )
            continue

        if any(s in path for s in ALLOWLIST_SUBSTRINGS):
            continue

        text = staged_blob(path).decode("utf-8", errors="ignore")
        is_decl = low.endswith((".dbk", ".dec", ".rec"))
        hits = scan_text(text, bare_cpf=not is_decl)
        if hits:
            problems.append(f"{path}: possible PII — {', '.join(hits)}")

    if problems:
        print("PII pre-commit check FAILED:\n", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        print("\nIf a hit is a false positive, allowlist the file in "
              "ALLOWLIST_SUBSTRINGS in tools/check_no_pii.py.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
