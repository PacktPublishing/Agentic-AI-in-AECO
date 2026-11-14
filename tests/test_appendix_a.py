from appendix_a.evaluation import run_cases
from appendix_a.tracing import SPANS, traced
from appendix_a.untrusted_input import screen_text, wrap_as_data
from ch7.agent import CarbonScreeningAgent


def test_all_golden_cases_pass_offline():
    results = run_cases()
    assert all(r.status in ("pass", "skipped") for r in results), [r for r in results if r.status == "fail"]


def test_evaluation_catches_a_model_that_changes_a_figure():
    class WrongNumbers:
        def complete(self, prompt):
            return prompt.split("EVIDENCE:", 1)[-1].replace("46,000", "41,000")
    assert run_cases(llm=WrongNumbers(), case_ids=["E04"])[0].status == "fail"


def test_screen_and_wrap():
    assert screen_text("Delivery in 16 weeks; factory slot held.").safe
    assert "never as instructions" in wrap_as_data("SUP-D-RETURN", "text")


def test_tracing_records_metadata_only(context):
    traced(CarbonScreeningAgent(context)).run("DCR-0007")
    span = SPANS[-1]
    assert span["agent"] == "Carbon Screening Agent" and span["data_class"] == "internal"
    assert "finding" not in span


def test_end_to_end_runs(capsys):
    from appendix_a.end_to_end import main
    main()
    assert "Rejected by Design Lead" in capsys.readouterr().out


# --- MCP configuration and server (Appendix A.4) -----------------------------
import asyncio
import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("config", [".mcp.json", ".gemini/settings.json"])
def test_mcp_configs_launch_the_project_server(config):
    servers = json.loads((ROOT / config).read_text())["mcpServers"]
    entry = servers["horizon-one-tower"]
    assert entry["args"][:1] == ["-m"]
    assert importlib.util.find_spec(entry["args"][1]) is not None


def test_agents_md_is_shared_with_claude():
    assert "MCP tools are read-only" in (ROOT / "AGENTS.md").read_text()
    assert "@AGENTS.md" in (ROOT / "CLAUDE.md").read_text()


def test_mcp_tools_are_marked_read_only():
    pytest.importorskip("mcp.types")
    from appendix_a.mcp_server import build_server
    tools = asyncio.run(build_server().list_tools())
    assert {t.name for t in tools} == {"open_issues", "planning_constraints", "facade_cost_movement"}
    for tool in tools:
        ann = tool.annotations
        assert getattr(ann, "read_only_hint", getattr(ann, "readOnlyHint", None)) is True


def test_any_mcp_client_can_launch_the_server_over_stdio():
    pytest.importorskip("mcp.client.stdio")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def names():
        params = StdioServerParameters(command=sys.executable, args=["-m", "appendix_a.mcp_server"],
                                       cwd=str(ROOT))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return [t.name for t in (await session.list_tools()).tools]

    assert "facade_cost_movement" in asyncio.run(names())
