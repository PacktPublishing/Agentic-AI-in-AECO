from __future__ import annotations

from horizon_core.agent_base import AgentContext

from ch5.design_intent_reviewer import DesignIntentReviewer
from ch5.generative_design_agent import generate_horizon_one_tower_options, generate_variation
from ch5.scorecard import generate_scorecard
from ch5.validation_agents import PlanningValidationAgent, StructuralFeasibilityAgent, summarise_shortlist

EXPECTED = {
    "A": dict(plot_efficiency="High", daylight_impact="Fails threshold"),
    "B": dict(plot_efficiency="Medium-high", daylight_impact="Meets threshold"),
    "C": dict(plot_efficiency="Medium", daylight_impact="Meets threshold"),
    "D": dict(plot_efficiency="High", daylight_impact="Marginal (close to threshold)"),
    "E": dict(plot_efficiency="Medium-low", daylight_impact="Meets threshold with margin"),
}


def test_generated_options_match_book_table() -> None:
    options = {o.option_id: o for o in generate_horizon_one_tower_options()}
    assert set(options) == set(EXPECTED)
    for option_id, expected in EXPECTED.items():
        assert options[option_id].plot_efficiency == expected["plot_efficiency"], option_id
        assert options[option_id].daylight_impact == expected["daylight_impact"], option_id


def test_option_a_requires_transfer_structure_and_higher_carbon() -> None:
    options = {o.option_id: o for o in generate_horizon_one_tower_options()}
    assert options["A"].structural_practicality == "Requires transfer structure at podium"
    assert options["A"].embodied_carbon_direction.startswith("Higher")


def test_option_c_requires_two_cores() -> None:
    options = {o.option_id: o for o in generate_horizon_one_tower_options()}
    assert options["C"].structural_practicality == "Requires two cores, higher cost"


def test_generate_variation_is_reusable_for_a_new_option() -> None:
    option_f = generate_variation(
        option_id="F",
        label="Future test option",
        tower_footprint_m2=500,
        podium_footprint_m2=1000,
        setback_strategy="Generous setback for a future scenario",
        podium_setback_m=8.0,
        storeys=20,
        core_count=1,
        requires_transfer_structure=False,
        floorplate_regularity="regular",
    )
    assert option_f.plot_efficiency == "Low"
    assert option_f.daylight_impact == "Meets threshold with margin"


def test_planning_validation_matches_book_outcomes(context: AgentContext) -> None:
    options = generate_horizon_one_tower_options()
    PlanningValidationAgent(context).run(options)
    by_id = {o.option_id: o for o in options}

    assert by_id["A"].planning_compliance == "Breach (height/setback/daylight)"
    assert by_id["B"].planning_compliance == "Compliant"
    assert by_id["C"].planning_compliance == "Compliant"
    assert by_id["D"].planning_compliance == "Conditional (needs daylight verification)"
    assert by_id["E"].planning_compliance == "Compliant"


def test_shortlist_matches_book_narrative(context: AgentContext) -> None:
    options = generate_horizon_one_tower_options()
    PlanningValidationAgent(context).run(options)
    groups = summarise_shortlist(options)

    assert [o.option_id for o in groups["eliminated"]] == ["A"]
    assert [o.option_id for o in groups["flagged"]] == ["D"]
    assert {o.option_id for o in groups["shortlisted"]} == {"B", "C", "E"}


def test_structural_feasibility_agent_flags_transfer_and_cores(context: AgentContext) -> None:
    options = generate_horizon_one_tower_options()
    finding = StructuralFeasibilityAgent(context).run(options)
    assert any("transfer structure" in r for r in finding.risks)
    assert any("two cores" in r for r in finding.risks)


def test_scorecard_has_expected_columns(context: AgentContext) -> None:
    options = generate_horizon_one_tower_options()
    PlanningValidationAgent(context).run(options)
    df = generate_scorecard(options)
    assert list(df.index) == ["A", "B", "C", "D", "E"]
    assert "Plot Efficiency" in df.columns
    assert "Planning Compliance" in df.columns


def test_design_intent_reviewer_carries_forward_b_and_e(context: AgentContext) -> None:
    options = generate_horizon_one_tower_options()
    PlanningValidationAgent(context).run(options)
    groups = summarise_shortlist(options)

    reviewer = DesignIntentReviewer(reviewer_role="Design Lead", audit_log=context.audit_log)
    decision = reviewer.decide(
        shortlisted=groups["shortlisted"],
        carry_forward_ids=["B", "E"],
        rationale="Best balance of compliance, structure, and daylight margin.",
    )
    assert decision.carried_forward == ["B", "E"]
    assert decision.not_carried_forward == ["C"]
    assert context.audit_log.entries_for("Design Intent Reviewer (human)")


def test_gia_counts_podium_storeys_once_and_b_meets_the_target(project) -> None:
    options = {o.option_id: o for o in generate_horizon_one_tower_options()}
    target = sum(project.massing_brief()["target_gia_by_use_m2"].values())
    assert target == 55000
    assert options["B"].gross_internal_area_m2 == 1550 * 24 + 3000 * 6
    assert options["B"].gross_internal_area_m2 >= target
    assert options["E"].gross_internal_area_m2 < target  # the trade-off the chapter describes


def test_height_and_setback_are_checked_separately(context: AgentContext) -> None:
    tall = generate_variation(option_id="T", label="Tall", tower_footprint_m2=1200, podium_footprint_m2=3000,
                              setback_strategy="3m", podium_setback_m=3.0, storeys=34, core_count=1,
                              requires_transfer_structure=False, floorplate_regularity="regular")
    PlanningValidationAgent(context).validate(tall)
    assert tall.breaches == ["height"]
