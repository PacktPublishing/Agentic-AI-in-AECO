"""Run Chapter 3's multi-agent design change review against Horizon One Tower.

    python -m ch3.run_ch3_demo
"""
from __future__ import annotations

from horizon_core.agent_base import AgentContext
from horizon_core.audit import AuditLog
from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.project import HorizonOneTowerProject

from ch3.orchestrator import AECOOrchestrator


def build_context() -> AgentContext:
    return AgentContext(
        project=HorizonOneTowerProject(),
        knowledge_base=AgentKnowledgeBase(),
        audit_log=AuditLog(),
    )


def main() -> None:
    context = build_context()
    orchestrator = AECOOrchestrator(context)

    request_id = "DCR-0007"
    change = context.project.design_change_request(request_id)
    result = orchestrator.run_change_review(request_id)

    print(orchestrator.trade_off_summary(result, change["title"]))

    print("\n--- Full findings ---")
    for key, finding in result["findings"].items():
        print(f"\n[{finding['agent']}] (confidence: {finding['confidence']})")
        print(finding["finding"])
        if finding["risks"]:
            print("Risks:", "; ".join(finding["risks"]))

    if result.get("conflicts"):
        print("\n--- Conflicts detected ---")
        for c in result["conflicts"]:
            print(f"  - {c}")
    if result.get("missing_evidence"):
        print("\n--- Missing / unconfirmed evidence ---")
        for m in result["missing_evidence"]:
            print(f"  - {m}")

    print("\n--- Paused review: the reviewer decides, then the graph resumes ---")
    paused = AECOOrchestrator(context, parallel=True, pause_for_review=True)
    state = paused.run_change_review(request_id)
    print("Paused before:", state.get("paused_at"))
    final = paused.record_decision(
        request_id, approved=False, reviewer="Design Lead",
        comments="Hold until the terracotta EPD and FM access review are received.")
    print("Final status:", final["review_status"])


if __name__ == "__main__":
    main()
