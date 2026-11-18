"""The Chapter 11 Fabrication Monitoring Agent (advisory only)."""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

from ch11.monitoring import maturity_c_h, risk_indicators


class FabricationMonitoringAgent(BaseAECOAgent):
    name = "Fabrication Monitoring Agent"
    chapter = 11
    reviewer_role = "Print Supervisor"
    data_class = "internal"
    purpose = "Report print risk indicators against documented limits and propose at most one adjustment."
    can_do = ["calculate indicators from the print log", "draft an adjustment proposal for the supervisor"]
    cannot_do = ["send an instruction to the printer", "override a safety function", "approve a proposal"]

    def run(self, request: str = "PAV-03") -> AgentFinding:
        p = self.context.project
        log = p.chapter_csv("fabrication", "pavilion_print_log.csv")
        limits = p.chapter_json("fabrication", "limits.json")
        ind = risk_indicators(log, limits)
        mat = maturity_c_h(log, layer=1, datum_c=limits["material"]["datum_c"])
        need = limits["material"]["maturity_required_c_h"]
        flagged = ind.loc[ind["flag"], "indicator"].tolist()
        text = (f"{len(flagged)} of 4 indicators outside limits ({', '.join(flagged)}). First-layer maturity "
                f"{mat:.0f} against {need:.0f} °C·h required. Speeding up would address the interlayer ratio "
                "but add load to under-matured layers; the indicators conflict.")
        finding = AgentFinding(
            agent=self.name, chapter=11,
            finding=self.context.llm.complete("EVIDENCE:\n" + text),
            sources=[ind["evidence"].iloc[0], ind["limit_source"].iloc[0]],
            assumptions=["Maturity calibration supplied by the structural engineer for MIX-PAV-02"],
            risks=["Interlayer ratio and maturity point in opposite directions"] if mat < need else [],
            confidence="Medium",
            recommended_action="Print supervisor and structural engineer to decide; the agent takes no controller action.",
        )
        self._log(task=f"Print monitoring {request}", sources=finding.sources,
                  tools_used=["risk_indicators", "maturity_c_h"], output_summary=text)
        return finding
