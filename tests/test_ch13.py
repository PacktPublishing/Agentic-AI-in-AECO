import pytest

from ch13.agent import FMFaultTriageAgent
from ch13.fm_triage import FMData, triage_hvac_fault


def test_identifier_mapping(project):
    fm = FMData(project)
    assert fm.resolve_asset("AHU_19_1") == fm.resolve_asset("MEP-AHU-019A") == "H1T-AHU-L19-01"
    with pytest.raises(KeyError):
        fm.resolve_asset("AHU_99_9")


def test_triage_uses_all_three_signals_and_cites_om(project):
    t = triage_hvac_fault(FMData(project), "H1T-AHU-L19-01")
    assert len(t["evidence"]) == 3 and t["om_citation"].startswith("OM-HVAC-AHU-019")
    assert t["open_maintenance_tasks"] == ["PPM-4411"]


def test_healthy_unit_is_not_flagged(project):
    assert triage_hvac_fault(FMData(project), "H1T-AHU-L07-01")["evidence"] == []


def test_agent_requires_fm_lead(context):
    assert "FM Lead approval required" in FMFaultTriageAgent(context).run("AHU_19_1").recommended_action
