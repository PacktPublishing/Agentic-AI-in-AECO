import pytest

pytest.importorskip("open3d")
pytest.importorskip("ifcopenshell")

from ch12.agent import AsBuiltInspectionAgent  # noqa: E402
from ch12.inspection import assess_scan, inspector_decision, load_targets  # noqa: E402


def test_bay_statuses(project):
    targets = load_targets(project.chapter_path("reality_capture", "HorizonOne_L04_Structure.ifc"))
    r = assess_scan(targets, project.chapter_path("reality_capture", "scan_L04_aligned.ply")).set_index("element")
    assert r.at["L04 slab bay S1", "status"] == "not assessable"
    assert r.at["L04 slab bay S2", "status"] == "breach" and r.at["L04 slab bay S2", "p98_mm"] == 21.6
    assert r.at["L04 slab bay S3", "status"] == "within tolerance"


def test_ticket_stays_draft_after_confirmation(context):
    agent = AsBuiltInspectionAgent(context)
    agent.run()
    issue, ticket = inspector_decision(agent.issues[0], True, "Site inspector", "19 to 23 mm outward")
    assert issue["status"] == "Confirmed" and ticket["status"] == "Draft - not issued"
