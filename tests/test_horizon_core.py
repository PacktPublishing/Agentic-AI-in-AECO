from __future__ import annotations

from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.project import HorizonOneTowerProject
from horizon_core.review import HumanReviewGate, detect_conflicts, detect_missing_evidence, review_gate
from horizon_core.schemas import AgentFinding, DocumentRecord
from horizon_core.tools import cost_tools, gis_tools, ifc_tools, pdf_tools


def test_project_overview_loads(project: HorizonOneTowerProject) -> None:
    overview = project.overview()
    assert overview["project_name"] == "Horizon One Tower"
    assert overview["tower_storeys"] > overview["podium_storeys"]


def test_planning_constraints_have_required_fields(project: HorizonOneTowerProject) -> None:
    constraints = project.planning_constraints()
    assert len(constraints) >= 5
    topics = {c.topic for c in constraints}
    assert {"Height", "Setback", "Daylight"}.issubset(topics)


def test_facade_cost_movement_is_an_increase(project: HorizonOneTowerProject) -> None:
    movement = cost_tools.facade_cost_movement(project.cost_plan())
    assert movement["direction"] == "increase"
    assert movement["movement_gbp"] == 60000
    assert movement["rate_confirmed"] is False


def test_pdf_parsing_returns_tagged_pages(project: HorizonOneTowerProject) -> None:
    pages = pdf_tools.parse_pdf(
        project.planning_report_pdf_path(), source="test", revision="P03", status="Approved"
    )
    assert len(pages) >= 5
    topics = {p["topic"] for p in pages}
    assert "Height" in topics
    assert all(p["text"] for p in pages)


def test_ifc_extraction_returns_spaces(project: HorizonOneTowerProject) -> None:
    spaces = ifc_tools.extract_spaces(
        project.architecture_ifc_path(), project.ifc_spaces_fallback_extract()
    )
    assert len(spaces) >= 10
    assert all({"ifc_id", "name", "type"}.issubset(s) for s in spaces)


def test_gis_tools_flood_and_servicing(project: HorizonOneTowerProject) -> None:
    gis = project.gis_constraints()
    assert "Flood Zone" in gis_tools.flood_risk_summary(gis)
    assert "pedestrian" in gis_tools.servicing_conflicts(gis)
    receptors = gis_tools.neighbouring_residential_receptors(gis)
    assert all(r["use"] == "Residential" for r in receptors)


def test_knowledge_base_retrieves_relevant_document() -> None:
    kb = AgentKnowledgeBase()
    kb.ingest(
        [
            DocumentRecord(
                project="Horizon One Tower",
                file="a.pdf",
                discipline="Planning",
                revision="P01",
                status="Approved",
                stage="Pre-Application",
                date="2026-01-01",
                source="test",
                text="Tower height must respect the townscape and skyline sensitivity area.",
                page=1,
                topic="Height",
            ),
            DocumentRecord(
                project="Horizon One Tower",
                file="b.pdf",
                discipline="Sustainability",
                revision="P01",
                status="Approved",
                stage="Pre-Application",
                date="2026-01-01",
                source="test",
                text="Embodied carbon should be reported using RICS methodology.",
                page=1,
                topic="Sustainability",
            ),
        ]
    )
    results = kb.query("What does the height and skyline policy say?", top_k=1)
    assert results
    top_doc, score = results[0]
    assert top_doc.topic == "Height"
    assert score > 0


def test_knowledge_base_status_filter() -> None:
    kb = AgentKnowledgeBase()
    kb.ingest(
        [
            DocumentRecord(
                project="Horizon One Tower",
                file="draft.pdf",
                discipline="Planning",
                revision="D01",
                status="Draft",
                stage="Concept",
                date="2026-01-01",
                source="test",
                text="Draft height policy note.",
            )
        ]
    )
    assert kb.query("height policy", status_in=["Approved"]) == []


def _finding(agent: str, action: str, confidence: str = "Medium", risks=None, sources=None) -> AgentFinding:
    return AgentFinding(
        agent=agent,
        finding="x",
        sources=sources or ["src"],
        risks=risks or [],
        confidence=confidence,
        recommended_action=action,
    )


def test_detect_conflicts_flags_disagreement() -> None:
    findings = [
        _finding("Cost Agent", "Proceed to commercial review."),
        _finding("Planning Risk Agent", "Do not proceed without further study."),
    ]
    assert detect_conflicts(findings)


def test_detect_conflicts_none_when_aligned() -> None:
    findings = [
        _finding("Cost Agent", "Proceed to commercial review."),
        _finding("Procurement Agent", "Proceed to commercial review required."),
    ]
    assert detect_conflicts(findings) == []


def test_detect_missing_evidence_flags_provisional_risk() -> None:
    findings = [_finding("Procurement Agent", "Proceed.", risks=["Availability is only provisional."])]
    assert detect_missing_evidence(findings)


def test_review_gate_routes_low_confidence_to_human_review() -> None:
    findings = [_finding("Sustainability Agent", "Proceed.", confidence="Low")]
    assert review_gate(findings) == "human_review"


def test_review_gate_routes_clean_findings_to_summary() -> None:
    findings = [
        _finding("Cost Agent", "Proceed to commercial review.", confidence="High"),
        _finding("Procurement Agent", "Proceed to commercial review.", confidence="High"),
    ]
    assert review_gate(findings) == "prepare_summary"


def test_human_review_gate_defaults_to_awaiting_review() -> None:
    gate = HumanReviewGate(reviewer_role="Design Lead")
    result = gate.submit(_finding("Cost Agent", "Proceed."))
    assert result.status == "Awaiting Review"


def test_human_review_gate_uses_approver_callback() -> None:
    gate = HumanReviewGate(reviewer_role="Design Lead", approver=lambda f: f.confidence == "High")
    approved = gate.submit(_finding("Cost Agent", "Proceed.", confidence="High"))
    rejected = gate.submit(_finding("Cost Agent", "Proceed.", confidence="Low"))
    assert approved.status == "Approved"
    assert rejected.status == "Rejected"
