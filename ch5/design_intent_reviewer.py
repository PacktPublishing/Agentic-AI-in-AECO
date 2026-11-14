"""Chapter 5, section 5.4: "Choosing Options Without Losing Design
Judgment" - the Design Intent Reviewer.

"The 'Design Intent Reviewer' functions as the bridge between these
quantitative metrics and the project's subjective design values... By
synthesizing the agent's evidence-based outputs with professional
architectural judgment..." "For Horizon One Tower, the team carries Options
B and E forward for [further technical development]."

This is deliberately not a :class:`~horizon_core.agent_base.BaseAECOAgent`
subclass and it does not call ``context.llm``. The whole point of this
class, and of the chapter section it implements, is that this decision is
not something an agent makes - it is a small, explicit record of a human
judgment call, kept in the same structured shape as everything else so it
stays in the audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from horizon_core.audit import AuditLog
from horizon_core.schemas import MassingOption


@dataclass
class DesignIntentDecision:
    reviewer_role: str
    carried_forward: List[str]
    not_carried_forward: List[str]
    rationale: str


class DesignIntentReviewer:
    """Records a human design lead's qualitative decision over a shortlist.

    Nothing here is inferred automatically - ``decide()`` takes the
    reviewer's own choice of option IDs and rationale as arguments. This
    mirrors the book directly: "Does the split massing in Option C read as
    one building or two? Does the stepped form in Option B suit the street
    it faces?" - those are judgment calls this codebase does not attempt to
    automate.
    """

    def __init__(self, reviewer_role: str, audit_log: Optional[AuditLog] = None) -> None:
        self.reviewer_role = reviewer_role
        self.audit_log = audit_log

    def decide(
        self,
        shortlisted: List[MassingOption],
        carry_forward_ids: List[str],
        rationale: str,
    ) -> DesignIntentDecision:
        shortlisted_ids = {o.option_id for o in shortlisted}
        carried = [oid for oid in carry_forward_ids if oid in shortlisted_ids]
        not_carried = [oid for oid in shortlisted_ids if oid not in carried]

        decision = DesignIntentDecision(
            reviewer_role=self.reviewer_role,
            carried_forward=carried,
            not_carried_forward=not_carried,
            rationale=rationale,
        )
        if self.audit_log:
            self.audit_log.record(
                agent="Design Intent Reviewer (human)",
                task="Choose which shortlisted massing options to carry forward",
                sources=[f"shortlist#Option {o.option_id}" for o in shortlisted],
                reviewer=self.reviewer_role,
                decision_status=f"Carried forward: {', '.join(carried) or 'none'}",
                output_summary=rationale,
            )
        return decision
