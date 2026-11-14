"""Run Chapter 4's Feasibility Risk Agent against Horizon One Tower.

    python -m ch4.run_ch4_demo
"""
from __future__ import annotations

from horizon_core.agent_base import AgentContext
from horizon_core.audit import AuditLog
from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.project import HorizonOneTowerProject

from ch4.feasibility_agent import FeasibilityRiskAgent


def build_context() -> AgentContext:
    return AgentContext(
        project=HorizonOneTowerProject(),
        knowledge_base=AgentKnowledgeBase(),
        audit_log=AuditLog(),
    )


def main() -> None:
    context = build_context()
    agent = FeasibilityRiskAgent(context)
    rows, market_finding = agent.run_with_market_context()

    header = f"{'Risk Area':<20} {'Finding':<52} {'Confidence':<10} Human Reviewer"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row.risk_area:<20} {row.finding:<52} {row.confidence:<10} {row.human_reviewer}")

    print(f"\n[Market Intelligence Agent] (confidence: {market_finding.confidence})")
    print(market_finding.finding)


if __name__ == "__main__":
    main()
