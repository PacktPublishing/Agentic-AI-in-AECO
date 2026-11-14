from __future__ import annotations

from horizon_core.agent_base import AgentContext

from ch3.agents import BimAuditAgent, CostAgent, OperationsAgent, PlanningRiskAgent, ProcurementAgent, SustainabilityAgent
from ch3.orchestrator import AECOOrchestrator


def test_cost_agent_reports_increase_as_in_chapter_text(context: AgentContext) -> None:
    finding = CostAgent(context).run("DCR-0007")
    assert "increases the façade package cost" in finding.recommended_action
    assert "Cost Plan Rev P06" in finding.sources
    assert finding.risks == ["Supplier rates have not yet been confirmed (indicative budget figure)."]


def test_sustainability_agent_flags_low_confidence(context: AgentContext) -> None:
    finding = SustainabilityAgent(context).run("DCR-0007")
    assert finding.confidence == "Low"


def test_bim_audit_agent_finds_open_facade_issues(context: AgentContext) -> None:
    finding = BimAuditAgent(context).run("DCR-0007")
    assert any("ISS-0144" in s for s in finding.sources)


def test_procurement_agent_flags_supplier_risk(context: AgentContext) -> None:
    finding = ProcurementAgent(context).run("DCR-0007")
    assert finding.risks


def test_planning_risk_agent_flags_submission_narrative(context: AgentContext) -> None:
    finding = PlanningRiskAgent(context).run("DCR-0007")
    assert finding.risks


def test_operations_agent_flags_fm_review(context: AgentContext) -> None:
    finding = OperationsAgent(context).run("DCR-0007")
    assert finding.risks


def test_orchestrator_runs_full_graph(context: AgentContext) -> None:
    orchestrator = AECOOrchestrator(context)
    result = orchestrator.run_change_review("DCR-0007")
    for key in ("bim", "cost", "sustainability", "procurement", "planning_risk", "operations"):
        assert result.get(key), f"missing {key} in result"
    assert result["review_status"] in {"Awaiting Review", "Approved", "Rejected"} or "Ready for normal approval" in result["review_status"]


def test_orchestrator_escalates_to_human_review_given_low_confidence_finding(context: AgentContext) -> None:
    # Sustainability Agent is Low confidence for this scenario, so the
    # review_gate should always escalate rather than auto-summarise.
    orchestrator = AECOOrchestrator(context)
    result = orchestrator.run_change_review("DCR-0007")
    assert result["review_status"] == "Awaiting Review"


def test_trade_off_summary_contains_all_sections(context: AgentContext) -> None:
    orchestrator = AECOOrchestrator(context)
    result = orchestrator.run_change_review("DCR-0007")
    summary = orchestrator.trade_off_summary(result, "Podium facade material substitution")
    for label in ("BIM impact", "Cost impact", "Sustainability impact", "Procurement impact", "Human review status", "Trace log"):
        assert label in summary


def test_parallel_graph_produces_the_same_findings(context: AgentContext) -> None:
    sequential = AECOOrchestrator(context).run_change_review("DCR-0007")
    parallel = AECOOrchestrator(context, parallel=True).run_change_review("DCR-0007")
    assert set(sequential["findings"]) == set(parallel["findings"])
    assert parallel["route"] == sequential["route"] == "human_review"


def test_paused_review_waits_and_resumes_with_decision(context: AgentContext) -> None:
    orchestrator = AECOOrchestrator(context, pause_for_review=True)
    paused = orchestrator.run_change_review("DCR-0007", thread_id="t1")
    assert paused["paused_at"] == ["human_review"]
    done = orchestrator.record_decision(
        "DCR-0007", approved=False, reviewer="Design Lead", comments="Await EPD", thread_id="t1")
    assert done["approved"] is False
    assert done["review_status"] == "Rejected by Design Lead"
    assert context.audit_log.entries[-1].reviewer == "Design Lead"


def test_custom_specialist_mapping_plugs_in(context: AgentContext) -> None:
    result = AECOOrchestrator(context, {"cost": CostAgent, "bim": BimAuditAgent}).run_change_review("DCR-0007")
    assert set(result["findings"]) == {"cost", "bim"}
