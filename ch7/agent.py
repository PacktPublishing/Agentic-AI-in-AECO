"""The Chapter 7 Carbon Screening Agent.

Plugs into the Chapter 3 orchestrator in place of (or next to) the simpler
Chapter 3 Sustainability Agent::

    AECOOrchestrator(context, {**DEFAULT_SPECIALISTS, "carbon": CarbonScreeningAgent})
"""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

from ch7.carbon import calculate_carbon, compare_options, load


class CarbonScreeningAgent(BaseAECOAgent):
    name = "Carbon Screening Agent"
    chapter = 7
    reviewer_role = "Sustainability Consultant"
    data_class = "internal"
    purpose = "Screen the embodied carbon of façade options from referenced quantities and factors."
    can_do = ["calculate A1-A3 screening totals from referenced records", "flag missing or mismatched evidence"]
    cannot_do = ["approve a material", "report a figure as verified", "update a project platform"]

    def run(self, request: str = "DCR-0007") -> AgentFinding:
        q, f, o = load(self.context.project)
        rows = calculate_carbon(q, f)
        comparison = compare_options(rows, o).set_index("option")
        a, b = comparison.loc["A"], comparison.loc["B"]
        complete = comparison["carbon_kgCO2e"].notna().all()
        if complete:
            text = (f"Option B (terracotta) screens at {b.carbon_kgCO2e:,.0f} kgCO2e against "
                    f"{a.carbon_kgCO2e:,.0f} for Option A ({b.change_pct:+.1f}%), per 1,000 m2, A1-A3, "
                    "panels and supports only.")
        else:
            text = "At least one option has incomplete evidence; no comparison total is reported."
        finding = AgentFinding(
            agent=self.name, chapter=7,
            finding=self.context.llm.complete("EVIDENCE:\n" + text),
            sources=sorted(set(rows["quantity_ref"]) | set(rows["factor_ref"].dropna())),
            assumptions=["Same screened area; common layers excluded", "Illustrative factors, not EPD values"],
            risks=["Product-specific EPD not yet supplied for terracotta"] if b.availability != "confirmed" else [],
            confidence="Low",
            recommended_action="Screening only - request product EPDs before relying on the comparison.",
        )
        self._log(task=f"Carbon screening for {request}", sources=finding.sources,
                  tools_used=["calculate_carbon", "compare_options"], output_summary=text)
        return finding
