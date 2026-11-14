"""The Chapter 8 Cost Intelligence Agent.

Explains cost movement between quantity snapshots R01 and R02 and keeps
unpriced work visible. It plugs into the Chapter 3 orchestrator under the
key ``cost_intelligence``.
"""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

from ch8.cost_demo import allowance_for
from ch8.ledger import load, movement, price, review


class CostIntelligenceAgent(BaseAECOAgent):
    name = "Cost Intelligence Agent"
    chapter = 8
    reviewer_role = "Cost Consultant"
    data_class = "confidential"
    purpose = "Explain supported cost movement between quantity snapshots and list unpriced work."
    can_do = ["price mapped quantities with nominated rates", "split movement into quantity and rate effects"]
    cannot_do = ["change the baseline", "issue a commercial recommendation", "estimate a missing rate"]

    def run(self, request: str = "DCR-0007") -> AgentFinding:
        quantities, rates, allowances = load(self.context.project)
        old, new = price(quantities, rates, "R01"), price(quantities, rates, "R02")
        m = movement(old, new)
        qty, rate = m["quantity_effect_gbp"].sum(), m["rate_effect_gbp"].sum()
        allowance = allowance_for(allowances, "R02") - allowance_for(allowances, "R01")
        rec = review(new, allowances)
        text = (f"R01 to R02: quantity effect GBP {qty:,.0f}, rate effect GBP {rate:,.0f}, access allowance "
                f"change GBP {allowance:,.0f}. Priced R02 subtotal GBP {rec['priced_subtotal_gbp']:,.0f}. "
                f"Unpriced: {', '.join(rec['unpriced_items']) or 'none'}.")
        finding = AgentFinding(
            agent=self.name, chapter=8, data_class="confidential",
            finding=self.context.llm.complete("EVIDENCE:\n" + text),
            sources=sorted(set(new["source_ref"]) | set(new["rate_source"].dropna())),
            assumptions=["Rates cover the defined assembly scope; access held as a package allowance"],
            risks=[f"{i} has no matching rate and is excluded from the subtotal" for i in rec["unpriced_items"]],
            confidence="Medium",
            recommended_action="Cost consultant to price unpriced items before the package forecast is updated.",
        )
        self._log(task=f"Cost movement for {request}", sources=finding.sources,
                  tools_used=["map_quantities", "price", "movement"], output_summary=text)
        return finding
