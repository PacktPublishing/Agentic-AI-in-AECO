"""Run Chapter 1's worked example against Horizon One Tower.

    python -m ch1.run_ch1_demo
"""
from __future__ import annotations

from horizon_core.agent_base import AgentContext
from horizon_core.audit import AuditLog
from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.project import HorizonOneTowerProject

from ch1.coordination_agent import DesignCoordinationSummaryAgent


def build_context() -> AgentContext:
    return AgentContext(
        project=HorizonOneTowerProject(),
        knowledge_base=AgentKnowledgeBase(),
        audit_log=AuditLog(),
    )


def main() -> None:
    context = build_context()
    agent = DesignCoordinationSummaryAgent(context)
    finding = agent.run()

    print(f"=== {agent.name} ===")
    print(finding.finding)
    print()
    print(f"Confidence: {finding.confidence}")
    print(f"Recommended action: {finding.recommended_action}")
    print(f"Sources ({len(finding.sources)}):")
    for s in finding.sources:
        print(f"  - {s}")
    if finding.risks:
        print("Risks:")
        for r in finding.risks:
            print(f"  - {r}")


if __name__ == "__main__":
    main()
