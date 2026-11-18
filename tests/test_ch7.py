import pandas as pd
import pytest

from ch7.agent import CarbonScreeningAgent
from ch7.carbon import calculate_carbon, compare_options, load


def test_screening_totals_match_chapter(project):
    q, f, o = load(project)
    c = compare_options(calculate_carbon(q, f), o).set_index("option")
    assert c.at["A", "carbon_kgCO2e"] == 50000 and c.at["B", "carbon_kgCO2e"] == 46000
    assert round(c.at["B", "change_pct"], 1) == -8.0


def test_missing_factor_blocks_total(project):
    q, f, o = load(project)
    c = compare_options(calculate_carbon(q, f[f["factor_id"] != "F-TER"]), o).set_index("option")
    assert pd.isna(c.at["B", "carbon_kgCO2e"]) and c.at["B", "calculation_status"] == "needs_evidence"


def test_scope_mismatch_is_reported(project):
    q, f, o = load(project)
    f.loc[f["factor_id"] == "F-SUP", "scope"] = "A1-A5"
    rows = calculate_carbon(q, f)
    assert rows["issues"].str.contains("scope mismatch").sum() == 2


def test_duplicate_records_rejected(project):
    q, f, _ = load(project)
    with pytest.raises(ValueError):
        calculate_carbon(pd.concat([q, q.head(1)]), f)


def test_agent_is_screening_only(context):
    finding = CarbonScreeningAgent(context).run()
    assert finding.confidence == "Low" and "Screening only" in finding.recommended_action
