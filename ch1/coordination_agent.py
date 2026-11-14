"""Chapter 1, section 1.8: "A worked example: the Design Coordination
Summary Agent" - filled in against the AECO Agent Design Template.

  Agent Identity: Design Coordination Summary Agent
  Purpose: Prepare a weekly summary of open coordination issues across
      disciplines for Horizon One Tower, so the Design Manager can chair the
      coordination meeting without re-reading every issue individually.
  Inputs: the BIM issue log, open RFIs, discipline meeting notes, and the
      drawing register.
  Tools: none beyond retrieval - this agent only reads and organises
      existing records, per Chapter 1's own worked example.
  Capabilities (can do): group open issues by discipline and zone; flag
      overdue items; flag issues with no linked coordination document; draft
      a short summary paragraph per group.
  Guardrails (cannot do): close issues, assign contractual responsibility,
      or issue instructions to any discipline. Chapter 1 is explicit that
      "it does not decide how issues should be resolved."
  Output: a structured coordination summary plus a short narrative, for the
      Design Manager to review before circulation - never sent directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

TODAY = date(2026, 9, 13)  # the "as of" date used across this book's examples


@dataclass
class CoordinationGroup:
    discipline: str
    zone: str
    open_issues: List[Dict[str, Any]] = field(default_factory=list)
    overdue_issues: List[Dict[str, Any]] = field(default_factory=list)
    unlinked_issues: List[Dict[str, Any]] = field(default_factory=list)


def _is_overdue(issue: Dict[str, Any], as_of: date = TODAY) -> bool:
    if issue["status"] == "Closed":
        return False
    due = date.fromisoformat(issue["due_date"])
    return due < as_of


def group_open_issues(issues: List[Dict[str, Any]], as_of: date = TODAY) -> List[CoordinationGroup]:
    """Group open issues by (discipline, zone) - the "can do" grouping step."""
    groups: Dict[tuple, CoordinationGroup] = {}
    for issue in issues:
        if issue["status"] == "Closed":
            continue
        key = (issue["discipline"], issue["zone"])
        group = groups.setdefault(key, CoordinationGroup(discipline=key[0], zone=key[1]))
        group.open_issues.append(issue)
        if _is_overdue(issue, as_of):
            group.overdue_issues.append(issue)
        if not issue.get("linked_document"):
            group.unlinked_issues.append(issue)
    return sorted(groups.values(), key=lambda g: (g.discipline, g.zone))


class DesignCoordinationSummaryAgent(BaseAECOAgent):
    name = "Design Coordination Summary Agent"
    chapter = 1
    reviewer_role = "Design Manager"
    data_class = "internal"
    purpose = (
        "Prepare a weekly summary of open coordination issues across "
        "disciplines for Horizon One Tower."
    )
    can_do = [
        "group open issues by discipline and zone",
        "flag overdue items",
        "flag issues missing a linked coordination document",
        "draft a short summary for the Design Manager to review",
    ]
    cannot_do = [
        "close issues",
        "assign contractual responsibility",
        "issue instructions",
    ]

    def run(self, request: str = "Prepare this week's design coordination summary") -> AgentFinding:
        self.assert_within_guardrails(request)

        issues = self.context.project.issue_log()
        rfis = self.context.project.rfis()
        groups = group_open_issues(issues)

        open_rfi_count = sum(1 for r in rfis if r["status"] == "Open")
        total_open = sum(len(g.open_issues) for g in groups)
        total_overdue = sum(len(g.overdue_issues) for g in groups)
        total_unlinked = sum(len(g.unlinked_issues) for g in groups)

        lines = [
            f"{total_open} open coordination issues across {len(groups)} discipline/zone groups, "
            f"{total_overdue} overdue, {total_unlinked} with no linked coordination document, "
            f"and {open_rfi_count} open RFIs outstanding."
        ]
        for g in groups:
            line = f"{g.discipline} - {g.zone}: {len(g.open_issues)} open"
            if g.overdue_issues:
                overdue_ids = ", ".join(i["issue_id"] for i in g.overdue_issues)
                line += f" ({len(g.overdue_issues)} overdue: {overdue_ids})"
            if g.unlinked_issues:
                unlinked_ids = ", ".join(i["issue_id"] for i in g.unlinked_issues)
                line += f"; no linked document: {unlinked_ids}"
            lines.append(line)

        prompt = "EVIDENCE:\n" + "\n".join(lines)
        narrative = self.context.llm.complete(prompt)

        sources = sorted({f"issue_log.json#{i['issue_id']}" for g in groups for i in g.open_issues})
        sources += sorted({f"rfis.json#{r['rfi_id']}" for r in rfis if r["status"] == "Open"})

        risks = []
        if total_overdue:
            risks.append(f"{total_overdue} issue(s) are past their due date.")
        if total_unlinked:
            risks.append(f"{total_unlinked} issue(s) have no linked coordination document.")

        finding = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=sources,
            assumptions=[f"'Overdue' is evaluated as of {TODAY.isoformat()}."],
            risks=risks,
            confidence="High" if not total_unlinked else "Medium",
            recommended_action="Design Manager to review before circulation at the coordination meeting.",
        )
        self._log(
            task=request,
            sources=sources,
            tools_used=["group_open_issues"],
            output_summary=narrative[:200],
        )
        return finding
