"""Appendix A.1: one design change reviewed by agents from six chapters.

    python -m appendix_a.end_to_end

DCR-0007 (podium façade, ACP to terracotta) goes through the Chapter 3
orchestrator with the Chapter 3 specialists plus the deeper agents from
Chapters 7, 8 and 9. The Chapter 9 agent handles confidential supplier
returns, so it runs behind the Chapter 14 governance gate. Specialists run
in parallel; the graph pauses before human review and resumes with the
Design Lead's decision. Every step lands in one audit trail.
"""

from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.context import default_context
from horizon_core.schemas import AgentFinding

from ch3.orchestrator import (
    DEFAULT_SPECIALISTS,
    AECOOrchestrator,
)
from ch7.agent import CarbonScreeningAgent
from ch8.agent import CostIntelligenceAgent
from ch9.agent import SupplierEvaluationAgent
from ch14.governance import GovernedAgent

GOVERNED_SOURCES = [
    "FAC-SPEC-R06",
    "SUP-A-RETURN",
    "SUP-B-RETURN",
    "SUP-C-RETURN",
    "SUP-D-RETURN",
]


class GovernedSupplierEvaluation(BaseAECOAgent):
    """Adapter so the governed Chapter 9 agent fits the orchestrator."""

    name = "Governed Supplier Evaluation"
    chapter = 14
    reviewer_role = "Commercial Manager"
    data_class = "confidential"
    purpose = ("Run the Chapter 9 evaluation only after the "
               "governance gate has approved it.")
    cannot_do = ["award a contract"]
    approved_by = "Digital Lead"

    def run(self, request: str) -> AgentFinding:
        governed = GovernedAgent(
            SupplierEvaluationAgent(self.context)
        )
        return governed.run(
            request,
            task_id="HOT-GOV-014",
            user_role="Commercial Manager",
            action="recommend",
            source_ids=GOVERNED_SOURCES,
            approved_by=self.approved_by,
        )


def main() -> None:
    context = default_context()
    specialists = {
        **DEFAULT_SPECIALISTS,
        "carbon": CarbonScreeningAgent,
        "cost_intelligence": CostIntelligenceAgent,
        "supplier_evaluation": GovernedSupplierEvaluation,
    }
    orchestrator = AECOOrchestrator(
        context,
        specialists,
        parallel=True,
        pause_for_review=True,
    )
    paused = orchestrator.run_change_review("DCR-0007")
    print(
        f"{len(paused['findings'])} specialist findings; paused before {paused['paused_at']}"
    )
    print(
        f"Missing or unconfirmed evidence: {len(paused['missing_evidence'])} item(s)\n"
    )
    final = orchestrator.record_decision(
        "DCR-0007",
        approved=False,
        reviewer="Design Lead",
        comments="Hold: terracotta EPD, return-panel rate and FM access review outstanding.",
    )
    print(
        orchestrator.trade_off_summary(
            final, "Podium façade material substitution"
        )
    )
    print(
        f"\nAudit trail: {len(context.audit_log.entries)} entries, last by {context.audit_log.entries[-1].agent}"
    )


if __name__ == "__main__":
    main()
