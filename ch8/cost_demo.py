"""Helpers the Chapter 8 listings import (``from cost_demo import ...``).

``map_quantities`` joins the quantity export to the BoQ map. It rejects
unmapped element types, duplicated identities and non-numeric quantities
instead of passing them through quietly, because a quantity that cannot be
traced to a BoQ item cannot be priced.

``allowance_for`` returns the package-level allowance for one revision.
Allowances are added after aggregation so they are not charged per element.
"""
from __future__ import annotations

import pandas as pd


def map_quantities(qto: pd.DataFrame, boq: pd.DataFrame) -> pd.DataFrame:
    if qto.duplicated(["revision", "item_id"]).any():
        raise ValueError("Duplicate (revision, item_id) in quantity export")
    mapped = qto.merge(boq, on="element_type", how="left", validate="many_to_one", indicator=True)
    unmapped = mapped.loc[mapped["_merge"].ne("both"), "item_id"].tolist()
    if unmapped:
        raise ValueError(f"Element types with no BoQ mapping: {unmapped}")
    mapped["quantity"] = pd.to_numeric(mapped["quantity"], errors="raise")
    return mapped.drop(columns="_merge")


def allowance_for(allowances: pd.DataFrame, revision: str) -> float:
    rows = allowances.loc[allowances["revision"].eq(revision), "amount_gbp"]
    if rows.empty:
        raise ValueError(f"No allowance record for revision {revision}")
    return float(rows.sum())
