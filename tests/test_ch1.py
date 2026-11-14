from __future__ import annotations

import pytest

from horizon_core.agent_base import AgentContext

from ch1.coordination_agent import DesignCoordinationSummaryAgent, group_open_issues


def test_group_open_issues_excludes_closed(context: AgentContext) -> None:
    issues = context.project.issue_log()
    groups = group_open_issues(issues)
    all_open_ids = {i["issue_id"] for g in groups for i in g.open_issues}
    assert "ISS-0128" not in all_open_ids  # closed in the fixture data


def test_group_open_issues_flags_overdue(context: AgentContext) -> None:
    issues = context.project.issue_log()
    groups = group_open_issues(issues)
    overdue_ids = {i["issue_id"] for g in groups for i in g.overdue_issues}
    assert "ISS-0142" in overdue_ids


def test_coordination_agent_returns_finding(context: AgentContext) -> None:
    agent = DesignCoordinationSummaryAgent(context)
    finding = agent.run()
    assert finding.agent == "Design Coordination Summary Agent"
    assert finding.sources
    assert finding.confidence in {"Low", "Medium", "High"}


def test_coordination_agent_guardrail_blocks_closing_issues(context: AgentContext) -> None:
    agent = DesignCoordinationSummaryAgent(context)
    with pytest.raises(PermissionError):
        agent.assert_within_guardrails("Please close issues ISS-0142 and ISS-0143")
