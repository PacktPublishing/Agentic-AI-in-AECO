from ch10.agent import PlanningProgressAgent
from ch10.progress import apply_spatial_observation, compare_progress, redeployment_option


def test_progress_findings(project):
    r = compare_progress(project.chapter_csv("programme", "schedule.csv"),
                         project.chapter_csv("programme", "progress.csv")).set_index("activity_id")
    assert r.at["L4-CONC", "variance_pp"] == -40 and r.at["L4-CONC", "finding"] == "behind_plan"
    assert r.at["L5-PREP", "finding"] == "verify_evidence"
    assert r.at["POD-REINF", "finding"] == "at_or_ahead"


def test_unverified_observation_is_not_used(project):
    obs = project.chapter_csv("programme", "progress.csv")
    obs.loc[obs["activity_id"] == "L4-CONC", "verified"] = False
    r = compare_progress(project.chapter_csv("programme", "schedule.csv"), obs).set_index("activity_id")
    assert r.at["L4-CONC", "finding"] == "verify_evidence"


def test_redeployment_option(project):
    option = redeployment_option(project.chapter_json("programme", "resource_scenario.json"))
    assert option["hold_allowance_gbp"] == 5760
    assert option["conditional_redeployment_allowance_gbp"] == 2760
    assert option["conditions"]


def test_confirmed_inspection_attaches_to_activity(project):
    issue = {"status": "Confirmed", "title": "L04 slab bay S2: slab edge outside tolerance",
             "links": {"activity": "L4-CONC", "zone": "L04-STR", "package": "HOT-POD-FAC-01"}}
    r = apply_spatial_observation(compare_progress(project.chapter_csv("programme", "schedule.csv"),
                                                   project.chapter_csv("programme", "progress.csv")), issue)
    assert "HOT-POD-FAC-01" in r.set_index("activity_id").at["L4-CONC", "quality_issue"]


def test_agent(context):
    assert PlanningProgressAgent(context).run().risks
