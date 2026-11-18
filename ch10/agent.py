"""The Chapter 10 Planning and Progress Agent."""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

from ch10.progress import compare_progress, redeployment_option


class PlanningProgressAgent(BaseAECOAgent):
    name = "Planning and Progress Agent"
    chapter = 10
    reviewer_role = "Project Planner"
    data_class = "internal"
    purpose = "Compare planned and verified progress at the agreed cut-off and price resource options."
    can_do = ["compare verified progress with the programme", "price a planner-supplied resource scenario"]
    cannot_do = ["update the programme", "instruct a crew", "commit cost"]

    def run(self, request: str = "HOT-L4-S01") -> AgentFinding:
        p = self.context.project
        report = compare_progress(p.chapter_csv("programme", "schedule.csv"), p.chapter_csv("programme", "progress.csv"))
        option = redeployment_option(p.chapter_json("programme", "resource_scenario.json"))
        lines = [f"{r.activity_id}/{r.zone_id}: {r.finding}"
                 + (f" ({r.variance_pp:+.0f} pp)" if r.finding != "verify_evidence" else "")
                 for r in report.itertuples()]
        lines.append(f"Hold allowance GBP {option['hold_allowance_gbp']:,}; conditional redeployment "
                     f"GBP {option['conditional_redeployment_allowance_gbp']:,}.")
        finding = AgentFinding(
            agent=self.name, chapter=10,
            finding=self.context.llm.complete("EVIDENCE:\n" + "\n".join(lines)),
            sources=sorted(set(report["evidence_ref"].dropna())) + ["schedule.csv (P06)", "PLAN-SCENARIO-01"],
            assumptions=["Cut-off 17 April 2026; planned percentages from the programme export"],
            risks=[f"{r.activity_id}: no usable observation" for r in report.itertuples() if r.finding == "verify_evidence"]
                  + option["conditions"],
            confidence="Medium",
            recommended_action="Planner to review the variance and confirm the redeployment conditions at the planning meeting.",
        )
        self._log(task=f"Progress review {request}", sources=finding.sources,
                  tools_used=["compare_progress", "redeployment_option"], output_summary=lines[0])
        return finding
