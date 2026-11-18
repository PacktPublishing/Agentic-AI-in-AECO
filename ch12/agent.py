"""The Chapter 12 As-Built Inspection Agent."""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

from ch12.inspection import CAPTURE, assess_scan, draft_issue, load_targets


class AsBuiltInspectionAgent(BaseAECOAgent):
    name = "As-Built Inspection Agent"
    chapter = 12
    reviewer_role = "Site Inspector"
    data_class = "internal"
    purpose = "Measure as-built deviation against the model and draft issues for inspector confirmation."
    can_do = ["measure deviation from tier 1 scan evidence", "draft BCF-style issues"]
    cannot_do = ["describe an element as compliant", "measure from photographs", "choose a remedy"]

    def run(self, request: str = "SCAN-L04-0428") -> AgentFinding:
        p = self.context.project
        targets = load_targets(p.chapter_path("reality_capture", "HorizonOne_L04_Structure.ifc"))
        results = assess_scan(targets, p.chapter_path("reality_capture", "scan_L04_aligned.ply"))
        self.issues = [draft_issue(r, targets) for _, r in results[results["status"] == "breach"].iterrows()]
        lines = [f"{r.element}: {r.status} (coverage {r.coverage:.2f}, p98 {r.p98_mm} mm)" for r in results.itertuples()]
        finding = AgentFinding(
            agent=self.name, chapter=12, evidence_tier=CAPTURE["evidence_tier"],
            finding=self.context.llm.complete("EVIDENCE:\n" + "\n".join(lines)),
            sources=[CAPTURE["scan_id"], "HorizonOne_L04_Structure.ifc"],
            assumptions=[f"Registration RMS {CAPTURE['registration_rms_mm']} mm; distances are unsigned"],
            risks=[f"{r.element} not assessable: rescan after clearing" for r in results.itertuples()
                   if r.status == "not assessable"],
            confidence="High" if self.issues else "Medium",
            recommended_action="Site inspector to confirm each draft issue on site before any ticket is issued.",
        )
        self._log(task=f"As-built inspection {request}", sources=finding.sources,
                  tools_used=["load_targets", "assess_scan", "draft_issue"], output_summary="; ".join(lines))
        return finding
