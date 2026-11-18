from __future__ import annotations

from horizon_core.agent_base import AgentContext

from ch6.audit_agent import (
    AuditAgent,
    facade_discrepancy_entry,
    facade_discrepancy_narrative,
    find_missing_parameters,
    group_findings,
    most_recent_facade_source,
)


def test_find_missing_parameters_scoped_to_6_1(context: AgentContext) -> None:
    bep = context.project.bim_execution_plan()
    bim_objects = context.project.bim_objects()
    scoped_bep = [r for r in bep if r.parameter in ("fire_rating", "asset_classification", "maintenance_access_clearance_mm")]
    gaps = find_missing_parameters(bim_objects, scoped_bep, categories=["Door", "Mechanical Asset"])
    object_ids = {g["object_id"] for g in gaps}
    assert {"DR-P3-014", "DR-P3-015", "DR-P3-016", "MEP-AHU-P3-01"}.issubset(object_ids)
    # Walls and rooms are excluded by the category filter even though they
    # have their own gaps in the full BEP scan.
    assert not any(g["object_category"] == "Room" for g in gaps)


def test_find_missing_parameters_full_scan_includes_rooms(context: AgentContext) -> None:
    bep = context.project.bim_execution_plan()
    bim_objects = context.project.bim_objects()
    gaps = find_missing_parameters(bim_objects, bep)
    room_gaps = [g for g in gaps if g["object_category"] == "Room"]
    assert len(room_gaps) == 4  # 3 retail classification gaps + 1 accessibility gap


def test_group_findings_batches_doors_into_one_row(context: AgentContext) -> None:
    bep = context.project.bim_execution_plan()
    bim_objects = context.project.bim_objects()
    gaps = find_missing_parameters(bim_objects, bep, categories=["Door"])
    entries = group_findings(gaps)
    fire_entry = next(e for e in entries if e.category == "Fire data")
    assert fire_entry.finding == "Batch of 3 doors carrying placeholder fire rating"
    assert set(fire_entry.object_ids) == {"DR-P3-014", "DR-P3-015", "DR-P3-016"}
    assert fire_entry.severity == "High"
    assert fire_entry.responsible_discipline == "Fire engineer"


def test_group_findings_falls_back_generically_for_unknown_rule() -> None:
    gaps = [{"object_id": "X-01", "object_category": "Window", "location": "Test", "name": None, "parameter": "u_value", "affects": []}]
    entries = group_findings(gaps)
    assert len(entries) == 1
    assert entries[0].category == "Other"
    assert "window" in entries[0].finding.lower()


def test_facade_documents_differ(context: AgentContext) -> None:
    doc_set = context.project.facade_document_set()
    entry = facade_discrepancy_entry(doc_set)
    assert entry is not None
    assert entry.category == "Document consistency"
    assert entry.severity == "High"


def test_most_recent_facade_source_is_the_specification(context: AgentContext) -> None:
    doc_set = context.project.facade_document_set()
    assert most_recent_facade_source(doc_set) == "facade_specification_P04.pdf"


def test_facade_discrepancy_narrative_mentions_all_three_sources(context: AgentContext) -> None:
    doc_set = context.project.facade_document_set()
    narrative = facade_discrepancy_narrative(doc_set)
    assert "facade_specification_P04.pdf" in narrative
    assert "ARC-DWG-PODF-001" in narrative
    assert "model" in narrative.lower()


def test_facade_discrepancy_entry_none_when_values_match() -> None:
    doc_set = {
        "parameter": "Test value",
        "unit": "W/m2K",
        "specification": {"document": "a.pdf", "revision": "P01", "value": 1.4, "date": "2026-01-01", "note": ""},
        "drawing": {"document": "b", "revision": "P01", "value": 1.4, "date": "2026-01-01", "note": ""},
        "model": {"object": "c", "value": 1.4, "date": "2026-01-01", "source": "Model", "note": ""},
    }
    assert facade_discrepancy_entry(doc_set) is None


def test_audit_agent_run_section_6_1(context: AgentContext) -> None:
    agent = AuditAgent(context)
    finding = agent.run()
    assert finding.agent == "Audit Agent"
    assert len(finding.risks) == 4
    assert finding.confidence == "High"


def test_audit_agent_run_bep_check_section_6_2(context: AgentContext) -> None:
    agent = AuditAgent(context)
    finding = agent.run_bep_check()
    assert any("placeholder fire rating" in r for r in finding.risks)
    assert any("maintenance access" in r for r in finding.risks)


def test_audit_agent_document_consistency_section_6_3(context: AgentContext) -> None:
    agent = AuditAgent(context)
    finding = agent.run_document_consistency_check()
    assert finding.confidence == "High"
    assert "exceeds the regulatory limiting value" in finding.recommended_action
    assert any("1.6" in r for r in finding.risks)


def test_audit_agent_compliance_log_matches_book_table(context: AgentContext) -> None:
    agent = AuditAgent(context)
    log = agent.generate_compliance_log()
    assert len(log) == 6

    by_category = {e.category: e for e in log}
    assert set(by_category) == {"Fire data", "Asset data", "Room data", "Accessibility",
                                "Document consistency", "Regulatory limit"}
    assert by_category["Regulatory limit"].severity == "High"

    assert by_category["Fire data"].severity == "High"
    assert by_category["Fire data"].responsible_discipline == "Fire engineer"
    assert by_category["Asset data"].severity == "Medium"
    assert by_category["Room data"].severity == "Low"
    assert by_category["Accessibility"].severity == "Medium"
    assert by_category["Document consistency"].severity == "High"

    high_severity = [e for e in log if e.severity == "High"]
    assert len(high_severity) == 3


def test_audit_agent_guardrail_blocks_approving_a_document(context: AgentContext) -> None:
    import pytest

    agent = AuditAgent(context)
    with pytest.raises(PermissionError):
        agent.assert_within_guardrails("Please approve a document for issue to the client")
