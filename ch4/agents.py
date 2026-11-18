"""Chapter 4's specialist agents, feeding the Feasibility Risk Agent.

Book section "Feasibility and Zoning - Multi-Agent Risk Assessment" names
four: the Zoning Compliance Agent (reads planning policy, zoning
classifications, and pre-application notes), the GIS Agent (site boundary,
flood zones, transport access, nearby building heights), the Environmental
Risk Agent (flood risk, daylight/overshadowing, contamination history), and
the Market Intelligence Agent (comparable schemes, achievable values,
absorption rates). Chapter 4: "As with the Zoning Compliance Agent, every
output carries its source and a confidence rating rather than a flat
statement of fact" - every agent below follows that rule through
``AgentFinding``.
"""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding
from horizon_core.tools import gis_tools


class ZoningComplianceAgent(BaseAECOAgent):
    name = "Zoning Compliance Agent"
    chapter = 4
    reviewer_role = "Planning Consultant"
    data_class = "internal"
    purpose = "Read planning policy and pre-application notes to flag height/massing risk."
    can_do = ["extract constraints from planning policy", "distinguish hard requirements from guidance"]
    cannot_do = ["interpret planning policy on the council's behalf", "confirm compliance"]

    def run(self, request: str = "height and massing feasibility") -> AgentFinding:
        constraints = self.context.project.planning_constraints()
        height = next(c for c in constraints if c.topic == "Height")
        pre_app = next(c for c in constraints if c.topic == "Pre-Application Advice")

        finding_text = (
            "Tower height may require townscape justification: "
            f"{height.description} ({height.clause_reference}). "
            f"Pre-application advice ({pre_app.clause_reference}) also noted a stepped massing "
            "strategy would be looked upon favourably, though this is guidance rather than a "
            "binding requirement."
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=[f"planning_policy.json#{height.topic}", f"planning_policy.json#{pre_app.topic}"],
            assumptions=["Reference scheme is 32 storeys, above the 30-storey townscape justification trigger."],
            risks=["Height exceeds the level at which townscape justification is required under Policy D9."],
            confidence="Medium",
            recommended_action="Planning consultant to confirm whether townscape justification is required and commission the supporting study.",
        )
        self._log(task=request, sources=result.sources, tools_used=["planning_constraints query"])
        return result


class GISAgent(BaseAECOAgent):
    name = "GIS Agent"
    chapter = 4
    reviewer_role = "Planning Consultant"
    data_class = "internal"
    purpose = "Simplify spatial layers (site boundary, flood zones, transport, neighbouring heights) into queryable constraints."
    can_do = ["summarise flood risk zone", "summarise servicing/transport conflicts", "summarise neighbouring building heights"]
    cannot_do = ["run a hydraulic flood model", "design a servicing route"]

    def run(self, request: str = "site constraints") -> AgentFinding:
        gis = self.context.project.gis_constraints()
        flood = gis_tools.flood_risk_summary(gis)
        servicing = gis_tools.servicing_conflicts(gis)

        finding_text = f"Flood risk: {flood} Servicing: {servicing}"
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["gis_constraints.json#flood_risk", "gis_constraints.json#transport"],
            risks=[
                "Site edge intersects the mapped Flood Zone 2 boundary.",
                "Proposed servicing route may conflict with pedestrian flow.",
            ],
            confidence="Medium",
            recommended_action="Environmental consultant and transport consultant to confirm flood and servicing findings against detailed design.",
        )
        self._log(task=request, sources=result.sources, tools_used=["gis_tools.flood_risk_summary", "gis_tools.servicing_conflicts"])
        return result


class EnvironmentalRiskAgent(BaseAECOAgent):
    name = "Environmental Risk Agent"
    chapter = 4
    reviewer_role = "Sustainability Consultant"
    data_class = "internal"
    purpose = "Assess flood risk, daylight/overshadowing, and contamination history."
    can_do = ["flag daylight risk to identified sensitive receptors", "flag where a technical study has not yet been run"]
    cannot_do = ["run a VSC/APSH daylight model", "confirm compliance with daylight guidance"]

    def run(self, request: str = "environmental constraints") -> AgentFinding:
        env = self.context.project.environmental_guidance()
        gis = self.context.project.gis_constraints()
        receptors = gis_tools.neighbouring_residential_receptors(gis)
        daylight = env["daylight_overshadowing"]

        finding_text = (
            "Podium massing may affect nearby residential windows: "
            f"{daylight['notes']} Sensitive receptors: "
            + ", ".join(r["name"] for r in receptors)
            + "."
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        risks = []
        if daylight.get("requires_technical_model_before_confirmation"):
            risks.append("No detailed VSC/APSH technical daylight model has been run yet - finding is based on massing sketches and general guidance only.")

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["environmental_guidance.json#daylight_overshadowing", "gis_constraints.json#neighbouring_buildings"],
            risks=risks,
            confidence="Low",
            recommended_action="Daylight consultant to run a detailed VSC/APSH study before this finding can be relied on for submission.",
        )
        self._log(task=request, sources=result.sources, tools_used=["gis_tools.neighbouring_residential_receptors"])
        return result


class MarketIntelligenceAgent(BaseAECOAgent):
    name = "Market Intelligence Agent"
    chapter = 4
    reviewer_role = "Development Manager"
    data_class = "confidential"
    purpose = "Organise comparable scheme data: achievable values, rents, and absorption rates."
    can_do = ["summarise comparable schemes", "flag stale or low-confidence comparables"]
    cannot_do = ["set the appraisal's value assumptions", "make a viability recommendation"]

    def run(self, request: str = "market context") -> AgentFinding:
        comparables = self.context.project.market_comparables()
        recent = [c for c in comparables if c["transaction_date"] >= "2025-01"]
        stale = [c for c in comparables if c["transaction_date"] < "2025-01"]

        finding_text = (
            f"{len(comparables)} comparable schemes reviewed within {max(c['distance_km'] for c in comparables)} km. "
            f"{len(recent)} transacted within the last ~18 months; {len(stale)} are older and carry less weight."
        )
        for c in comparables:
            if c.get("delivery_risk_notes") and c["delivery_risk_notes"] != "None reported.":
                finding_text += f" {c['scheme']}: {c['delivery_risk_notes']}"
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=[f"market_comparables.json#{c['scheme']}" for c in comparables],
            risks=[f"{c['scheme']} comparable is from {c['transaction_date']}, older than ~18 months." for c in stale],
            confidence="Medium",
            recommended_action="Valuer to confirm which comparables remain appropriate given market movement since transaction date.",
        )
        self._log(task=request, sources=result.sources, tools_used=["market_comparables query"])
        return result
