"""The human approval gate - the tenth part of the agent anatomy (1.7), and
the "review_gate" conflict-resolution pattern from Chapter 3's "Conflict
resolution and the human-in-the-loop" section.

Chapter 3 is explicit that a conflict resolution gate does not need to be
complicated: check whether specialist agents agree, whether the evidence is
complete, and whether the topic is too risky to proceed without human
review. This module implements exactly that pattern as a reusable component,
so it is not re-invented per chapter.

No agent in this codebase is allowed to skip this gate for anything the book
calls a "human decision" - substitutions, planning interpretations, cost
recommendations, and design choices all route through here.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from .schemas import AgentFinding, ReviewResult

# Confidence ranking used to decide whether a finding is strong enough to
# avoid an automatic escalation - mirrors "low confidence" being one of the
# book's explicit escalation triggers.
_CONFIDENCE_RANK = {"Low": 0, "Medium": 1, "High": 2}


def detect_conflicts(findings: List[AgentFinding]) -> List[str]:
    """Very small conflict heuristic: agents whose recommended actions
    disagree about whether to proceed are flagged as being in tension.

    This is deliberately simple - the book's point is not that conflict
    detection needs to be clever, only that it must not be skipped. A small
    negation check keeps it honest: "do not proceed" should not be read as
    a vote to proceed just because it contains the word "proceed".
    """
    _NEGATIONS = ("do not proceed", "not proceed", "cannot proceed", "avoid proceeding", "without further")

    def _supports_proceeding(text: str) -> bool:
        lowered = text.lower()
        if any(neg in lowered for neg in _NEGATIONS):
            return False
        return "proceed" in lowered or "commercial review required" in lowered

    proceed_votes = {f.agent: _supports_proceeding(f.recommended_action) for f in findings}
    if len(set(proceed_votes.values())) > 1:
        return [
            f"{agent}: {'supports proceeding' if vote else 'flags a concern before proceeding'}"
            for agent, vote in proceed_votes.items()
        ]
    return []


def detect_missing_evidence(findings: List[AgentFinding]) -> List[str]:
    """Findings with no cited sources or any explicit risk about missing/
    unconfirmed evidence are treated as "missing evidence" per Chapter 3."""
    missing = []
    for f in findings:
        if not f.sources:
            missing.append(f"{f.agent}: no sources cited")
        for risk in f.risks:
            if any(word in risk.lower() for word in ("not yet confirmed", "not yet been confirmed", "provisional", "not yet run")):
                missing.append(f"{f.agent}: {risk}")
    return missing


def review_gate(
    findings: List[AgentFinding],
    high_risk_decision: bool = False,
) -> str:
    """Chapter 3's ``review_gate`` pattern: decide the next routing step.

    Returns one of ``"human_review"`` or ``"prepare_summary"``, matching the
    two branches wired into the LangGraph conditional edge in
    ``ch3.orchestrator``.
    """
    if high_risk_decision:
        return "human_review"
    if detect_conflicts(findings):
        return "human_review"
    if detect_missing_evidence(findings):
        return "human_review"
    if any(_CONFIDENCE_RANK[f.confidence] == 0 for f in findings):
        return "human_review"
    return "prepare_summary"


class HumanReviewGate:
    """The Human Review Authority from Chapters 1 and 3.

    By default nothing is auto-approved: every finding routed here comes back
    ``"Awaiting Review"``, because deciding what is safe to auto-approve is
    itself a project-specific policy choice, not something this teaching
    codebase should assume. Pass an ``approver`` callback to simulate (for
    tests, or a real reviewer's decision service) an actual human decision.
    """

    def __init__(
        self,
        reviewer_role: str,
        approver: Optional[Callable[[AgentFinding], bool]] = None,
    ) -> None:
        self.reviewer_role = reviewer_role
        self._approver = approver

    def submit(self, finding: AgentFinding, comments: Optional[str] = None) -> ReviewResult:
        if self._approver is None:
            return ReviewResult(
                reviewer_role=self.reviewer_role,
                status="Awaiting Review",
                comments=comments,
            )
        approved = self._approver(finding)
        return ReviewResult(
            reviewer_role=self.reviewer_role,
            status="Approved" if approved else "Rejected",
            comments=comments,
        )
