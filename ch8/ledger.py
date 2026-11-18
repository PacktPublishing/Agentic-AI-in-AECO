"""Chapter 8 cost ledger: the listings as reusable functions."""
from __future__ import annotations

from math import isfinite

import pandas as pd

from ch8.cost_demo import allowance_for, map_quantities


def load(project):
    get = lambda name: project.chapter_csv("cost", name)  # noqa: E731
    return map_quantities(get("quantities.csv"), get("boq_map.csv")), get("rates.csv"), get("allowances.csv")


def price(quantities: pd.DataFrame, rates: pd.DataFrame, revision: str) -> pd.DataFrame:
    q = quantities.loc[quantities["revision"].eq(revision)]
    r = rates.loc[rates["revision"].eq(revision)].drop(columns="revision")
    if q.empty or r[["spec_id", "unit", "quantity_basis"]].isna().any().any():
        raise ValueError("Missing snapshot or rate lookup key")
    if r["currency"].ne("GBP").any():
        raise ValueError("This exercise accepts GBP only")
    lines = q.merge(r, on=["spec_id", "unit", "quantity_basis"], how="left", validate="many_to_one", indicator=True)
    valid = lines["_merge"].eq("both")
    for field in ["quantity", "rate_gbp"]:
        lines[field] = pd.to_numeric(lines[field], errors="coerce")
        valid &= lines[field].map(lambda x: isfinite(x) and x >= 0)
    valid &= lines[["source_ref", "rate_source"]].notna().all(axis=1)
    valid &= pd.to_datetime(lines["rate_date"], errors="coerce").notna()
    lines["amount_gbp"] = (lines["quantity"] * lines["rate_gbp"]).where(valid)
    lines["review_status"] = "Awaiting cost consultant"
    return lines.drop(columns="_merge")


def movement(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    m = old.merge(new, on="item_id", how="outer", suffixes=("_old", "_new"), validate="one_to_one", indicator=True)
    comparable = m["_merge"].eq("both")
    for field in ["spec_id", "unit", "quantity_basis"]:
        comparable &= m[f"{field}_old"].eq(m[f"{field}_new"])
    comparable &= m[["amount_gbp_old", "amount_gbp_new"]].notna().all(axis=1)
    m["quantity_effect_gbp"] = ((m["quantity_new"] - m["quantity_old"]) * m["rate_gbp_old"]).where(comparable)
    m["rate_effect_gbp"] = (m["quantity_new"] * (m["rate_gbp_new"] - m["rate_gbp_old"])).where(comparable)
    return m


def review(new: pd.DataFrame, allowances: pd.DataFrame, revision: str = "R02") -> dict:
    return {
        "project_id": "HOT",
        "change_id": "DEMO-CHG-008",
        "priced_subtotal_gbp": new["amount_gbp"].sum(min_count=1) + allowance_for(allowances, revision),
        "unpriced_items": new.loc[new["amount_gbp"].isna(), "item_id"].tolist(),
        "package_forecast_gbp": None,
        "review_status": "Awaiting cost consultant",
        "approved": False,
    }
