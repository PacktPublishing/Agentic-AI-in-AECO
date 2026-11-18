"""Run Chapter 6's BIMGUARD workflow against Horizon One Tower.

    python -m ch6.run_ch6_demo
"""
from __future__ import annotations

from horizon_core.agent_base import AgentContext
from horizon_core.audit import AuditLog
from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.project import HorizonOneTowerProject

from ch6.audit_agent import AuditAgent
from ch6.compliance_log import display_compliance_log, render_compliance_log


def build_context() -> AgentContext:
    return AgentContext(
        project=HorizonOneTowerProject(),
        knowledge_base=AgentKnowledgeBase(),
        audit_log=AuditLog(),
    )


def main() -> None:
    context = build_context()
    agent = AuditAgent(context)

    print("=== 6.1 From Clash Detection to Semantic Auditing ===")
    finding_6_1 = agent.run()
    print(finding_6_1.finding)
    print(f"Confidence: {finding_6_1.confidence} | {len(finding_6_1.risks)} instance(s) flagged\n")

    print("=== 6.2 Checking BIM Against Project Information Requirements ===")
    finding_6_2 = agent.run_bep_check()
    print(finding_6_2.finding, "\n")

    print("=== 6.3 Reviewing Drawings and Specifications Together ===")
    finding_6_3 = agent.run_document_consistency_check()
    print(finding_6_3.finding)
    print(f"Recommended action: {finding_6_3.recommended_action}\n")

    print("=== 6.4 Creating Trusted Design Review Logs ===")
    log = agent.generate_compliance_log()
    df = render_compliance_log(log)
    display_compliance_log(df)

    high_severity = [e for e in log if e.severity == "High"]
    print(f"\n{len(high_severity)} high-severity item(s) to escalate before the next coordination issue:")
    for e in high_severity:
        print(f"  - [{e.category}] {e.finding} -> {e.responsible_discipline}")


if __name__ == "__main__":
    main()
