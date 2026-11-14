"""Chapter 4's Feasibility Risk Agent.

"A team assembling a first-pass feasibility view for Horizon One Tower
might build a Feasibility Risk Agent that orchestrates the outputs of the
Zoning Compliance, GIS, Environmental Risk, and Market Intelligence agents
into one report. Its purpose is deliberately narrow: it does not make the
development decision. Its job is to prepare a structured risk note for the
development manager, architect, planner, and client."

:func:`FeasibilityRiskAgent.run` reproduces the book's worked example table
exactly: Height and massing / Daylight impact / Flood risk / Servicing
access, each with a risk-area, finding, evidence source, confidence, and
named human reviewer.
"""
from __future__ import annotations

from typing import List

from horizon_core.agent_base import AgentContext
from horizon_core.schemas import FeasibilityRiskItem

from ch4.agents import EnvironmentalRiskAgent, GISAgent, MarketIntelligenceAgent, ZoningComplianceAgent


class FeasibilityRiskAgent:
    """Not itself a model call - a narrow orchestrator over four specialist
    agents, exactly as Chapter 4 describes. Kept as a plain class (rather
    than a ``BaseAECOAgent``) because its whole job is composition: it has
    no retrieval or tool-use of its own beyond calling the four agents.
    """

    def __init__(self, context: AgentContext) -> None:
        self.context = context
        self.zoning_agent = ZoningComplianceAgent(context)
        self.gis_agent = GISAgent(context)
        self.environmental_agent = EnvironmentalRiskAgent(context)
        self.market_agent = MarketIntelligenceAgent(context)

    def run(self, request: str = (
        "Prepare a first-pass feasibility risk summary for Horizon One Tower, covering "
        "height, massing, access, environmental constraints, public realm, and approval risk. "
        "Use only approved feasibility sources and show the evidence used."
    )) -> List[FeasibilityRiskItem]:
        zoning = self.zoning_agent.run(request)
        gis = self.gis_agent.run(request)
        environmental = self.environmental_agent.run(request)

        rows = [
            FeasibilityRiskItem(
                risk_area="Height and massing",
                finding="Tower height may require townscape justification",
                evidence_source="Local planning policy, early massing note",
                confidence=zoning.confidence,
                human_reviewer="Planning consultant",
            ),
            FeasibilityRiskItem(
                risk_area="Daylight impact",
                finding="Podium massing may affect nearby residential windows",
                evidence_source="Daylight guidance, site context model",
                confidence=environmental.confidence,
                human_reviewer="Daylight consultant",
            ),
            FeasibilityRiskItem(
                risk_area="Flood risk",
                finding="Site edge intersects low-risk flood mapping layer",
                evidence_source="GIS flood data",
                confidence=gis.confidence,
                human_reviewer="Environmental consultant",
            ),
            FeasibilityRiskItem(
                risk_area="Servicing access",
                finding="Proposed servicing route may conflict with pedestrian flow",
                evidence_source="Transport note",
                confidence=gis.confidence,
                human_reviewer="Transport consultant",
            ),
        ]

        self.context.audit_log.record(
            agent="Feasibility Risk Agent",
            task=request,
            sources=zoning.sources + gis.sources + environmental.sources,
            output_summary=f"{len(rows)} feasibility risk rows prepared",
        )
        return rows

    def run_with_market_context(self, request: str = "market feasibility") -> tuple:
        """Optional extension: also returns the Market Intelligence Agent's
        finding alongside the four-row risk table, for chapters/uses that
        want commercial viability context too (the book keeps market
        intelligence as a separate signal rather than a risk-table row)."""
        rows = self.run()
        market_finding = self.market_agent.run(request)
        return rows, market_finding
