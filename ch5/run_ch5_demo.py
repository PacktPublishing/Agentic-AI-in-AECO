"""Run Chapter 5's generative design workflow against Horizon One Tower.

    python -m ch5.run_ch5_demo
"""
from __future__ import annotations

from horizon_core.agent_base import AgentContext
from horizon_core.audit import AuditLog
from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.project import HorizonOneTowerProject

from ch5.design_intent_reviewer import DesignIntentReviewer
from ch5.generative_design_agent import generate_horizon_one_tower_options
from ch5.scorecard import display_scorecard, generate_scorecard
from ch5.validation_agents import PlanningValidationAgent, StructuralFeasibilityAgent, summarise_shortlist


def build_context() -> AgentContext:
    return AgentContext(
        project=HorizonOneTowerProject(),
        knowledge_base=AgentKnowledgeBase(),
        audit_log=AuditLog(),
    )


def main() -> None:
    context = build_context()

    options = generate_horizon_one_tower_options()

    planning_agent = PlanningValidationAgent(context)
    structural_agent = StructuralFeasibilityAgent(context)
    planning_finding = planning_agent.run(options)
    structural_finding = structural_agent.run(options)

    print(f"[{planning_finding.agent}]\n{planning_finding.finding}\n")
    print(f"[{structural_finding.agent}]\n{structural_finding.finding}\n")

    df = generate_scorecard(options)
    display_scorecard(df)

    groups = summarise_shortlist(options)
    print(f"\nEliminated: {[o.option_id for o in groups['eliminated']]}")
    print(f"Flagged (needs verification): {[o.option_id for o in groups['flagged']]}")
    print(f"Shortlisted: {[o.option_id for o in groups['shortlisted']]}")

    reviewer = DesignIntentReviewer(reviewer_role="Design Lead", audit_log=context.audit_log)
    decision = reviewer.decide(
        shortlisted=groups["shortlisted"],
        carry_forward_ids=["B", "E"],
        rationale=(
            "Option B offers a strong balance of compliance and structural efficiency; Option E gives "
            "the best daylight margins with a more conservative, podium-led approach. Option C is "
            "technically compliant but its structural complexity and cost are not justified for this site."
        ),
    )
    print(f"\n[Design Intent Reviewer - {decision.reviewer_role}]")
    print(f"Carried forward: {decision.carried_forward}")
    print(f"Not carried forward: {decision.not_carried_forward}")
    print(f"Rationale: {decision.rationale}")


if __name__ == "__main__":
    main()
