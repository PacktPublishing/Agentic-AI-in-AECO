"""Appendix A.4: exposing Horizon One Tower tools over the Model Context Protocol.

A read-only MCP server lets any MCP-capable assistant use the project's
deterministic tools without bespoke integration code. Only read tools are
exposed; anything that changes a record stays behind the Chapter 14 gate.

    pip install mcp
    python -m appendix_a.mcp_server        # serves over stdio

Tested with MCP Python SDK 2.3 (and written to fall back to the 1.x
class name). Check the SDK documentation for later changes.
"""

from __future__ import annotations

import json

from horizon_core.project import HorizonOneTowerProject
from horizon_core.tools import cost_tools

project = HorizonOneTowerProject()


def open_issues(zone: str = "") -> str:
    """Open coordination issues, optionally filtered by zone."""
    issues = [
        i
        for i in project.issue_log()
        if i["status"] != "Closed"
        and (not zone or zone in i["zone"])
    ]
    return json.dumps(issues, indent=1)


def planning_constraints() -> str:
    """Planning constraints with clause references (Chapter 4)."""
    return json.dumps(
        [
            c.model_dump()
            for c in project.planning_constraints()
        ],
        indent=1,
    )


def facade_cost_movement() -> str:
    """Cost movement for the podium façade substitution (Chapter 3)."""
    return json.dumps(
        cost_tools.facade_cost_movement(project.cost_plan()),
        indent=1,
    )


TOOLS = [
    open_issues,
    planning_constraints,
    facade_cost_movement,
]


def build_server():  # pragma: no cover - optional dependency
    """Register the read-only tools with the MCP SDK.

    MCP Python SDK 2.x names the server class ``MCPServer``; 1.x called
    it ``FastMCP``. Both are supported here.
    """
    from mcp.types import ToolAnnotations

    try:
        from mcp.server.mcpserver import MCPServer as Server
    except ImportError:
        from mcp.server.fastmcp import FastMCP as Server

    server = Server("horizon-one-tower")
    read_only = ToolAnnotations(readOnlyHint=True)
    for fn in TOOLS:
        server.tool(annotations=read_only)(fn)
    return server


if __name__ == "__main__":  # pragma: no cover
    try:
        build_server().run()
    except ImportError:
        print(
            "Install the MCP SDK first: pip install 'mcp[cli]'. Tools available:",
            ", ".join(f.__name__ for f in TOOLS),
        )
