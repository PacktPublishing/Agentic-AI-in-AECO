"""The Chapter 9 Supplier Evaluation Agent.

Scores the podium façade offers and prepares a review pack. Supplier notes
are untrusted text: they are screened before any model sees them (see
``appendix_a/untrusted_input.py``) and they never change a score.
Plugs into the Chapter 3 orchestrator under ``supplier_evaluation``; Chapter
14 wraps it with the governance gate because the inputs are confidential.
"""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

from appendix_a.untrusted_input import screen_text
from ch9.evaluation import evaluate_all, load_bids, review_pack


class SupplierEvaluationAgent(BaseAECOAgent):
    name = "Supplier Evaluation Agent"
    chapter = 9
    reviewer_role = "Commercial Manager"
    data_class = "confidential"
    purpose = "Compare supplier responses against the package baseline with published weights."
    can_do = ["validate supplier returns", "score complete bids", "flag unresolved evidence"]
    cannot_do = ["award a contract", "approve a supplier", "change the weights after scoring"]

    def run(self, request: str = "HOT-POD-FAC-01") -> AgentFinding:
        package, bids, raw = load_bids(self.context.project)
        matrix = evaluate_all(bids, package)
        self.last_review_pack = review_pack(package, bids, matrix)
        screened = {r["vendor"]: screen_text(r["supplier_note"]) for r in raw.to_dict("records")}
        lines = []
        for row in sorted(matrix, key=lambda r: (r["rank"] is None, r["rank"] or 0)):
            if row["score"] is None:
                lines.append(f"Supplier {row['vendor']}: not scored ({'; '.join(row['flags'])}).")
            else:
                lines.append(f"Supplier {row['vendor']}: rank {row['rank']}, score {row['score']:.1f}, "
                             f"total GBP {row['total_gbp']:,.0f}.")
        risks = [f"Supplier {v}: note withheld from the model ({s.reasons[0]})"
                 for v, s in screened.items() if not s.safe]
        finding = AgentFinding(
            agent=self.name, chapter=9, data_class="confidential",
            finding=self.context.llm.complete("EVIDENCE:\n" + "\n".join(lines)),
            sources=[b.quote_ref for b in bids],
            assumptions=["Weights and anchors fixed before scoring (DEMO-EVAL-01)"],
            risks=risks + [f"Supplier {r['vendor']}: {f}" for r in matrix for f in r["flags"]],
            confidence="Medium",
            recommended_action="Commercial Manager to review the matrix; no supplier is recommended by the agent.",
        )
        self._log(task=f"Supplier evaluation for {request}", sources=finding.sources,
                  tools_used=["Bid validation", "evaluate_all", "screen_text"], output_summary=lines[0])
        return finding
