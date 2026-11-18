"""The Chapter 8 listings, exactly as printed, in chapter order.

    python -m ch8.listings

The chapter reads its CSVs from a folder called "data" next to cost_demo.py.
In the repository they live in data/horizon_one_tower/cost, so DATA points
there; that is the only change from the printed code. Reusable versions are
in ch8/ledger.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
DATA = Path(__file__).resolve().parents[1] / "data" / "horizon_one_tower" / "cost"

# --- Listing 8.1 ---
from pathlib import Path
import pandas as pd
from cost_demo import map_quantities, allowance_for

data = DATA  # printed as Path("data"); see the module docstring
qto = pd.read_csv(data / "quantities.csv")
boq = pd.read_csv(data / "boq_map.csv")
rates = pd.read_csv(data / "rates.csv")
allowances = pd.read_csv(data / "allowances.csv")

quantities = map_quantities(qto, boq)


# --- Listing 8.2 ---
from math import isfinite

def price(revision: str) -> pd.DataFrame:
    q = quantities.loc[quantities["revision"].eq(revision)]
    r = rates.loc[rates["revision"].eq(revision)].drop(
        columns="revision"
    )
    if q.empty or r[
        ["spec_id", "unit", "quantity_basis"]
    ].isna().any().any():
        raise ValueError("Missing snapshot or rate lookup key")
    if r["currency"].ne("GBP").any():
        raise ValueError("This exercise accepts GBP only")

    lines = q.merge(
        r, on=["spec_id", "unit", "quantity_basis"], how="left",
        validate="many_to_one", indicator=True
    )
    valid = lines["_merge"].eq("both")
    for field in ["quantity", "rate_gbp"]:
        lines[field] = pd.to_numeric(lines[field], errors="coerce")
        valid &= lines[field].map(lambda x: isfinite(x) and x >= 0)
    valid &= lines[["source_ref", "rate_source"]].notna().all(axis=1)
    valid &= pd.to_datetime(lines["rate_date"], errors="coerce").notna()

    lines["amount_gbp"] = (
        lines["quantity"] * lines["rate_gbp"]
    ).where(valid)
    lines["review_status"] = "Awaiting cost consultant"
    return lines.drop(columns="_merge")


old = price("R01")
new = price("R02")


# --- Listing 8.3 ---
movement = old.merge(
    new, on="item_id", how="outer",
    suffixes=("_old", "_new"),
    validate="one_to_one", indicator=True
)

comparable = movement["_merge"].eq("both")
for field in ["spec_id", "unit", "quantity_basis"]:
    comparable &= movement[f"{field}_old"].eq(
        movement[f"{field}_new"]
    )
comparable &= movement[
    ["amount_gbp_old", "amount_gbp_new"]
].notna().all(axis=1)

movement["quantity_effect_gbp"] = (
    (movement["quantity_new"] - movement["quantity_old"])
    * movement["rate_gbp_old"]
).where(comparable)

movement["rate_effect_gbp"] = (
    movement["quantity_new"]
    * (movement["rate_gbp_new"] - movement["rate_gbp_old"])
).where(comparable)

allowance_change = (
    allowance_for(allowances, "R02")
    - allowance_for(allowances, "R01")
)


# --- Listing 8.4 ---
review = {
    "project_id": "HOT",
    "change_id": "DEMO-CHG-008",
    "priced_subtotal_gbp": (
        new["amount_gbp"].sum(min_count=1)
        + allowance_for(allowances, "R02")
    ),
    "unpriced_items": new.loc[
        new["amount_gbp"].isna(), "item_id"
    ].tolist(),
    "package_forecast_gbp": None,
    "review_status": "Awaiting cost consultant",
    "approved": False
}


print(new[["item_id", "quantity", "rate_gbp", "amount_gbp"]].to_string(index=False))
print(movement[["item_id", "quantity_effect_gbp", "rate_effect_gbp"]].to_string(index=False))
print("Allowance change:", allowance_change)
print(review)
