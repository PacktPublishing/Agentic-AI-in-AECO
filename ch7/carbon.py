"""Chapter 7: embodied carbon screening for the podium façade options.

The functions are the chapter's listings, made reusable: the quantities,
factors and option data come from ``data/horizon_one_tower/carbon`` instead
of being typed inline. The rules are unchanged:

* every quantity must carry a reference, and every factor a scope, indicator
  and reference;
* units, scope (A1-A3) and indicator (GWP-total) must match, or the line is
  not calculated;
* an option only gets a total when all of its components are present.

The language model never calculates carbon. It may only explain the table.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

REQUIRED_COMPONENTS = {"panels", "supports"}


def calculate_carbon(q: pd.DataFrame, f: pd.DataFrame) -> pd.DataFrame:
    if q.empty or q.duplicated(["option", "component"]).any():
        raise ValueError("Provide unique, non-empty component records.")
    rows = q.merge(f, on=["factor_id", "component"], how="left", validate="many_to_one")
    for column in ["quantity", "factor"]:
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
    checks = {
        "invalid quantity": rows["quantity"].map(lambda x: pd.notna(x) and math.isfinite(x) and x >= 0),
        "missing/invalid factor": rows["factor"].map(lambda x: pd.notna(x) and math.isfinite(x)),
        "unit mismatch": rows["unit"].eq("kg") & rows["factor_unit"].eq("kgCO2e/kg"),
        "scope mismatch": rows["scope"].eq("A1-A3"),
        "indicator mismatch": rows["indicator"].eq("GWP-total"),
        "missing quantity reference": rows["quantity_ref"].fillna("").str.strip().ne(""),
        "missing factor reference": rows["factor_ref"].fillna("").str.strip().ne(""),
    }
    rows["issues"] = [
        "; ".join(name for name, passed in checks.items() if not passed.fillna(False).iloc[i])
        for i in range(len(rows))
    ]
    rows["carbon_kgCO2e"] = (rows["quantity"] * rows["factor"]).where(rows["issues"].eq(""))
    return rows


def compare_options(rows: pd.DataFrame, options: pd.DataFrame, baseline: str = "A") -> pd.DataFrame:
    groups = rows.groupby("option")
    totals = groups["carbon_kgCO2e"].agg(lambda values: values.sum(min_count=len(values)))
    coverage = groups["component"].agg(lambda values: set(values) == REQUIRED_COMPONENTS)
    result = options.merge(totals.where(coverage).rename("carbon_kgCO2e"), on="option", how="left",
                           validate="one_to_one")
    base = result.set_index("option").at[baseline, "carbon_kgCO2e"]
    result["change_pct"] = (100 * (result["carbon_kgCO2e"] / base - 1)
                            if pd.notna(base) and base > 0 else float("nan"))
    result["calculation_status"] = result["carbon_kgCO2e"].notna().map(
        {True: "screening_only", False: "needs_evidence"})
    return result


def review_record(rows: pd.DataFrame, comparison: pd.DataFrame, change_id: str = "DEMO-HOT-POD-01") -> dict:
    complete = bool(comparison["carbon_kgCO2e"].notna().all())
    return {
        "record_id": str(uuid4()),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project": "Horizon One Tower",
        "change_id": change_id,
        "calculation_version": "chapter7-demo-v2",
        "area_m2": 1000,
        "scope": "A1-A3: panels and supports only",
        "evidence_quality": "illustrative teaching data; unverified for project use",
        "assumptions": ["Same screened area; common layers excluded"],
        "exclusions": ["Other facade components; transport to site; installation",
                       "maintenance; replacement; operational energy; end-of-life"],
        "line_items": json.loads(rows.to_json(orient="records")),
        "options": json.loads(comparison.to_json(orient="records")),
        "calculation_status": "complete_for_screening" if complete else "incomplete",
        "evidence_status": "illustrative_unverified",
        "review_status": "pending_multidisciplinary_review",
        "approval_status": "not_approved",
        "reviewer_role": "Sustainability consultant",
        "reviewer": None,
        "required_follow_up": ["Verify quantities, factors and full assembly scope",
                               "Obtain supplier evidence and confirm availability",
                               "Complete technical, energy, planning and commercial reviews"],
    }


def load(project):
    q = project.chapter_csv("carbon", "quantities.csv")
    f = project.chapter_csv("carbon", "factors.csv")
    o = project.chapter_csv("carbon", "options.csv")
    return q, f, o
