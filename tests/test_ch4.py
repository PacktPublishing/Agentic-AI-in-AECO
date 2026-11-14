from __future__ import annotations

from horizon_core.agent_base import AgentContext

from ch4.agents import EnvironmentalRiskAgent, GISAgent, MarketIntelligenceAgent, ZoningComplianceAgent
from ch4.feasibility_agent import FeasibilityRiskAgent


def test_zoning_compliance_agent_flags_townscape_justification(context: AgentContext) -> None:
    finding = ZoningComplianceAgent(context).run()
    assert finding.risks
    assert finding.confidence == "Medium"


def test_gis_agent_flags_flood_and_servicing(context: AgentContext) -> None:
    finding = GISAgent(context).run()
    assert len(finding.risks) == 2


def test_environmental_risk_agent_is_low_confidence_pending_study(context: AgentContext) -> None:
    finding = EnvironmentalRiskAgent(context).run()
    assert finding.confidence == "Low"
    assert finding.risks


def test_market_intelligence_agent_flags_stale_comparable(context: AgentContext) -> None:
    finding = MarketIntelligenceAgent(context).run()
    assert any("2023" in r for r in finding.risks)


def test_feasibility_risk_agent_produces_four_row_table(context: AgentContext) -> None:
    rows = FeasibilityRiskAgent(context).run()
    assert len(rows) == 4
    risk_areas = [r.risk_area for r in rows]
    assert risk_areas == ["Height and massing", "Daylight impact", "Flood risk", "Servicing access"]

    by_area = {r.risk_area: r for r in rows}
    assert by_area["Height and massing"].confidence == "Medium"
    assert by_area["Daylight impact"].confidence == "Low"
    assert by_area["Flood risk"].confidence == "Medium"
    assert by_area["Servicing access"].confidence == "Medium"
    assert by_area["Height and massing"].human_reviewer == "Planning consultant"
    assert by_area["Daylight impact"].human_reviewer == "Daylight consultant"


def test_feasibility_risk_agent_with_market_context(context: AgentContext) -> None:
    rows, market_finding = FeasibilityRiskAgent(context).run_with_market_context()
    assert len(rows) == 4
    assert market_finding.agent == "Market Intelligence Agent"
