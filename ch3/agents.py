"""Chapter 3's specialist agents.

The book's code names four: the BIM Audit Agent, Cost Agent, Sustainability
Agent, and Procurement Agent (section "Coordinating Multiple Specialist
Agents"). The "Conflict resolution and the human-in-the-loop" section then
narrates two more taking part in the same review - the Planning Risk Agent
and the Operations Agent - to make the point that disagreement between
valid professional priorities is normal and should be preserved, not
smoothed away. All six are implemented here as equal citizens, each a
:class:`~horizon_core.agent_base.BaseAECOAgent` subclass, so
``ch3.orchestrator`` can route to exactly the four the book's code shows, or
the full six the book's narrative describes - "allowing future ones" is
just adding another node to the graph in ``ch3.orchestrator``, not writing a
new kind of agent.

Every agent below reviews the same concrete scenario: Horizon One Tower's
podium facade material substitution (``design_change_requests.json``,
``DCR-0007``), retrieving its own slice of project memory exactly as
Chapter 3 describes: "The specialist agents below retrieve different slices
of the same controlled project context."
"""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding
from horizon_core.tools import cost_tools


class BimAuditAgent(BaseAECOAgent):
    name = "BIM Audit Agent"
    chapter = 3
    reviewer_role = "BIM Manager"
    data_class = "internal"
    purpose = "Review the federated model for coordination issues touching a proposed design change."
    can_do = ["identify open coordination issues linked to the change area", "flag missing coordination between disciplines"]
    cannot_do = ["approve or reject the design change", "instruct a discipline to resolve an issue"]

    def run(self, request_id: str = "DCR-0007") -> AgentFinding:
        self.context.project.design_change_request(request_id)  # validates the request exists
        issues = self.context.project.issue_log()
        related = [
            i for i in issues
            if i["zone"] in ("Facade - Podium",) and i["status"] != "Closed"
        ]

        sources = [f"issue_log.json#{i['issue_id']}" for i in related]
        if related:
            finding_text = (
                f"{len(related)} open coordination issue(s) touch the podium facade zone. "
                + "; ".join(f"{i['issue_id']}: {i['description']}" for i in related)
            )
            risks = [f"{i['issue_id']} is unresolved and should be closed before the facade package is finalised." for i in related]
        else:
            finding_text = "No open coordination issues currently touch the podium facade zone."
            risks = []

        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)
        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=sources,
            risks=risks,
            confidence="Medium" if related else "High",
            recommended_action=(
                "Bracket depth and fire-stopping interfaces require review before proceeding."
                if related else "No BIM coordination blockers identified."
            ),
        )
        self._log(task=f"BIM audit for {request_id}", sources=sources, tools_used=["issue_log query"])
        return result


class CostAgent(BaseAECOAgent):
    name = "Cost Agent"
    chapter = 3
    reviewer_role = "Commercial Manager"
    data_class = "confidential"
    purpose = "Compare the cost movement between the current and proposed facade options."
    can_do = ["compute cost movement from the approved cost plan", "flag whether a rate is confirmed"]
    cannot_do = ["approve the cost movement", "commit to a supplier price"]

    def run(self, request_id: str = "DCR-0007") -> AgentFinding:
        self.context.project.design_change_request(request_id)  # validates the request exists
        movement = cost_tools.facade_cost_movement(self.context.project.cost_plan())

        direction_word = {"decrease": "saving", "increase": "cost increase", "no change": "no change"}[movement["direction"]]
        finding_text = (
            f"Substituting {movement['current_option']} for {movement['proposed_option']} across "
            f"{movement['quantity_m2']:,} sqm gives an estimated GBP {abs(movement['movement_gbp']):,} "
            f"{direction_word} ({movement['movement_pct']}%)."
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        risks = []
        if not movement["rate_confirmed"]:
            risks.append("Supplier rates have not yet been confirmed (indicative budget figure).")

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["Cost Plan Rev P06", "cost_plan.json#facade_package"],
            assumptions=[movement["quantity_assumption"]],
            risks=risks,
            confidence="Medium" if not movement["rate_confirmed"] else "High",
            recommended_action=(
                "Potential saving, subject to quantity confirmation - commercial review required."
                if movement["direction"] == "decrease"
                else "Terracotta increases the façade package cost - commercial review required."
            ),
        )
        self._log(task=f"Cost review for {request_id}", sources=result.sources, tools_used=["facade_cost_movement"])
        return result


class SustainabilityAgent(BaseAECOAgent):
    name = "Sustainability Agent"
    chapter = 3
    reviewer_role = "Sustainability Consultant"
    data_class = "internal"
    purpose = "Compare embodied carbon and service life between the current and proposed facade options."
    can_do = ["compare embodied carbon figures", "flag evidence quality (product-specific EPD vs generic benchmark)"]
    cannot_do = ["approve a material on sustainability grounds alone", "certify an EPD"]

    def run(self, request_id: str = "DCR-0007") -> AgentFinding:
        self.context.project.design_change_request(request_id)
        workbook = self.context.project.sustainability_workbook()["facade_package"]
        current, proposed = workbook["current_option"], workbook["proposed_option"]

        carbon_delta = proposed["embodied_carbon_kgco2e_per_m2"] - current["embodied_carbon_kgco2e_per_m2"]
        direction = "lower" if carbon_delta < 0 else "higher" if carbon_delta > 0 else "unchanged"
        finding_text = (
            f"{proposed['name']} shows {direction} embodied carbon than {current['name']} "
            f"({proposed['embodied_carbon_kgco2e_per_m2']} vs {current['embodied_carbon_kgco2e_per_m2']} kgCO2e/m2) "
            f"and a longer service life ({proposed['service_life_years']} vs {current['service_life_years']} years). "
            f"{workbook['notes']}"
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        risks = []
        if proposed["evidence_quality"] == "Low":
            risks.append(f"{proposed['name']} embodied carbon figure is not yet backed by a product-specific EPD.")

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["sustainability_workbook.json#facade_package"],
            risks=risks,
            confidence="Low" if proposed["evidence_quality"] == "Low" else "Medium",
            recommended_action=(
                "Lower-carbon option available, but evidence is incomplete - request product-specific EPD "
                "before relying on the figure for reporting."
            ),
        )
        self._log(task=f"Sustainability review for {request_id}", sources=result.sources, tools_used=["sustainability_workbook comparison"])
        return result


class ProcurementAgent(BaseAECOAgent):
    name = "Procurement Agent"
    chapter = 3
    reviewer_role = "Procurement Manager"
    data_class = "confidential"
    purpose = "Check supplier availability and lead time for the proposed facade option."
    can_do = ["compare candidate suppliers", "flag lead-time or availability risk"]
    cannot_do = ["place an order", "commit to a supplier"]

    def run(self, request_id: str = "DCR-0007") -> AgentFinding:
        self.context.project.design_change_request(request_id)
        tracker = self.context.project.procurement_tracker()["facade_package"]
        suppliers = tracker["proposed_option_suppliers"]

        finding_text = (
            f"{len(suppliers)} suitable supplier(s) identified for the proposed facade option. "
            + tracker["substitution_risk_summary"]
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        risks = [f"{s['name']}: {s['risk_notes']}" for s in suppliers if s.get("risk_notes")]

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["procurement_tracker.json#facade_package"],
            risks=risks,
            confidence="Medium",
            recommended_action="Two suitable suppliers identified; one has lead-time risk - proceed to commercial review with lead time confirmed before order.",
        )
        self._log(task=f"Procurement review for {request_id}", sources=result.sources, tools_used=["procurement_tracker query"])
        return result


class PlanningRiskAgent(BaseAECOAgent):
    name = "Planning Risk Agent"
    chapter = 3
    reviewer_role = "Planning Consultant"
    data_class = "internal"
    purpose = "Check whether a design change affects what was described in the planning submission."
    can_do = ["compare the proposed change against the planning submission narrative", "flag if planning consultant sign-off is needed"]
    cannot_do = ["approve a change on planning grounds", "submit an amendment to the local authority"]

    def run(self, request_id: str = "DCR-0007") -> AgentFinding:
        change = self.context.project.design_change_request(request_id)
        ref = change["planning_submission_reference"]

        finding_text = (
            f"The design change ({change['option_a']} to {change['option_b']}) touches material described in "
            f"{ref['document']}. {ref['note']}"
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=[f"design_change_requests.json#{request_id}.planning_submission_reference"],
            risks=["Facade material change may affect the approved design/character narrative and require planning consultant sign-off before submission."],
            confidence=ref["confidence"],
            recommended_action="Planning consultant to confirm whether this is a non-material change before proceeding.",
        )
        self._log(task=f"Planning risk review for {request_id}", sources=result.sources, tools_used=["design_change_requests query"])
        return result


class OperationsAgent(BaseAECOAgent):
    name = "Operations Agent"
    chapter = 3
    reviewer_role = "FM Lead"
    data_class = "internal"
    purpose = "Check whether a design change affects facilities management and facade maintenance access."
    can_do = ["compare the proposed change against the Operations & Maintenance outline", "flag unresolved FM review items"]
    cannot_do = ["approve a change on operational grounds", "commit to an FM budget"]

    def run(self, request_id: str = "DCR-0007") -> AgentFinding:
        change = self.context.project.design_change_request(request_id)
        ops = change["operations_notes"]

        finding_text = f"Operations & Maintenance impact of {change['option_b']}: {ops['note']}"
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=[f"design_change_requests.json#{change['request_id']}.operations_notes"],
            risks=["Facade access/maintenance strategy has not yet been reviewed by Facilities Management for the proposed material."] if ops.get("requires_fm_review") else [],
            confidence=ops["confidence"],
            recommended_action="Facilities Management to review access and replacement logistics before proceeding.",
        )
        self._log(task=f"Operations review for {request_id}", sources=result.sources, tools_used=["design_change_requests query"])
        return result
