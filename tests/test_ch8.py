import pytest

from ch8.agent import CostIntelligenceAgent
from ch8.cost_demo import allowance_for, map_quantities
from ch8.ledger import load, movement, price


def test_movement_split_matches_chapter(project):
    quantities, rates, allowances = load(project)
    m = movement(price(quantities, rates, "R01"), price(quantities, rates, "R02"))
    assert m["quantity_effect_gbp"].sum() == 32500
    assert m["rate_effect_gbp"].sum() == 36000
    assert allowance_for(allowances, "R02") - allowance_for(allowances, "R01") == 7000


def test_unrated_return_panel_stays_unpriced(project):
    quantities, rates, _ = load(project)
    new = price(quantities, rates, "R02").set_index("item_id")
    assert new["amount_gbp"].isna()["POD-RET-TER"]


def test_unmapped_element_type_rejected(project):
    qto = project.chapter_csv("cost", "quantities.csv")
    boq = project.chapter_csv("cost", "boq_map.csv")
    with pytest.raises(ValueError, match="no BoQ mapping"):
        map_quantities(qto, boq[boq["spec_id"] != "TER-RET-01"])


def test_agent_lists_unpriced_work(context):
    finding = CostIntelligenceAgent(context).run()
    assert any("POD-RET-TER" in r for r in finding.risks)
