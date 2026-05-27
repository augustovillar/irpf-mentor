"""Integration tests that exercise tools through the FastMCP dispatch layer.

Unlike test_tools.py (which calls the plain functions), these go through
`mcp.call_tool`, which is the path a real MCP client triggers: argument
schema validation, invocation, and content serialization. This catches
registration/signature/serialization regressions the function-level tests
can't.

Tests are sync and drive the async dispatch via asyncio.run, so no async
pytest plugin/config is needed.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from irpf_mcp.server import mcp

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "fixtures" / "synthetic-2026.dbk"


def _call(name: str, args: dict) -> list:
    """Call a tool through dispatch; return parsed JSON payload(s)."""
    async def _run():
        result = await mcp.call_tool(name, args)
        content = result[0] if isinstance(result, tuple) else result
        parsed = []
        for block in content:
            text = getattr(block, "text", None)
            if text is not None:
                parsed.append(json.loads(text))
        return parsed

    return asyncio.run(_run())


def _list_tools() -> set[str]:
    return {t.name for t in asyncio.run(mcp.list_tools())}


def test_all_tools_registered() -> None:
    names = _list_tools()
    expected = {"decode", "explain", "list_records", "lookup_perguntas",
                "validate", "sanity", "diff", "encode", "tax",
                "sources", "map_document"}
    assert expected <= names, f"Missing tools: {expected - names}"


def test_explain_via_dispatch() -> None:
    payload = _call("explain", {"record_type": "IR", "field_name": "NR_CPF"})
    assert payload, "explain returned no content"
    field = payload[0]["field"]
    assert field["nome"] == "NR_CPF"
    assert field["tamanho"] == 11


def test_validate_via_dispatch_rejects_bad_value() -> None:
    payload = _call("validate",
                    {"record_type": "IR", "field_name": "EXERCICIO", "value": "abc"})
    assert payload[0]["ok"] is False
    assert payload[0]["errors"]


def test_lookup_via_dispatch() -> None:
    payload = _call("lookup_perguntas",
                    {"query": "previdencia privada PGBL", "top_k": 3})
    assert payload, "lookup returned nothing"
    assert all("titulo" in p for p in payload)


def test_map_document_unsupported_is_structured() -> None:
    payload = _call("map_document", {"content": "random text"})
    assert payload[0]["ok"] is False
    assert "available_sources" in payload[0]


@pytest.mark.skipif(not FIXTURE.exists(),
                    reason="Run tools/redact.py to generate the fixture first")
def test_decode_via_dispatch() -> None:
    payload = _call("decode", {"path": str(FIXTURE)})
    assert payload[0]["header"]["nome"] == "REG_HEADER"
    assert len(payload[0]["records"]) == 16
