from ch15.enterprise import (AGENT_REGISTRY, agent_portfolio, governance_maturity, pilot_decision,
                             pilot_decisions, roadmap, screen_use_cases, skills_matrix, workflow_card)


def _screen(project):
    return screen_use_cases(project.chapter_csv("enterprise", "use_case_backlog.csv")).set_index("use_case")


def test_four_criteria_and_value_measure(project):
    s = _screen(project)
    assert s.at["Weekly design coordination review", "first_pilot"]
    assert "information identified" in s.at["FM fault triage", "missing"]
    assert "review can be assigned" in s.at["Contractual response drafting", "missing"]
    assert "value can be measured" in s.at["AI meeting minutes for every meeting", "missing"]


def test_high_risk_candidate_is_not_a_first_pilot(project):
    s = _screen(project)
    assert s.at["Print monitoring advisory", "candidate"] and not s.at["Print monitoring advisory", "first_pilot"]


def test_pilot_decisions_follow_the_chapter(project):
    d = pilot_decisions(project.chapter_csv("enterprise", "pilot_results.csv")).set_index("use_case")
    assert d.at["Weekly design coordination review", "decision"] == "scale"
    assert d.at["BEP compliance log", "decision"] == "redesign"
    assert d.at["Progress variance report", "decision"] == "retest"
    assert d.at["Contractual response drafting", "decision"] == "stop"


def test_unacceptable_risk_always_stops():
    r = {"cases_tested": 50, "pass_rate": 0.99, "review_minutes_agent": 5, "review_minutes_manual": 60,
         "value_change_pct": -90, "risk_acceptable": False, "main_error_source": ""}
    assert pilot_decision(r)[0] == "stop"


def test_workflow_card_answers_all_seven_questions():
    import ch1.coordination_agent  # noqa: F401
    card = workflow_card(AGENT_REGISTRY["Design Coordination Summary Agent"])
    assert len(card) == 7 and all(card.values())


def test_portfolio_and_controls(project):
    portfolio = agent_portfolio()
    assert {1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13}.issubset(set(portfolio["chapter"].dropna().astype(int)))
    m = governance_maturity(portfolio, project.chapter_json("enterprise", "governance_checklist.json")).set_index("id")
    assert m.at["G1", "coverage_pct"] == 100 and m.at["G2", "coverage_pct"] == 100


def test_roadmap_has_the_four_stages(project):
    plan = roadmap(_screen(project).reset_index(),
                   pilot_decisions(project.chapter_csv("enterprise", "pilot_results.csv")))
    assert [s["stage"] for s in plan] == ["Foundation", "Controlled pilots", "Live deployment", "Responsible scale"]
    assert "Contractual response drafting" in plan[3]["actions"][0]


def test_skills_are_the_chapter_list(project):
    m = skills_matrix(project.chapter_csv("enterprise", "skills_survey.csv"))
    assert set(m["skill"]) == {"task_design", "information_structuring", "retrieval", "evaluation",
                               "workflow_mapping", "governance", "assurance", "communication"}
    assert (m["gap"] >= 0).all()
