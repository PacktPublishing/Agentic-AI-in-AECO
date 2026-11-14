"""The Chapter 9 listings, exactly as printed, in chapter order.

    python -m ch9.listings

Reusable versions (reading data/horizon_one_tower/procurement) are in
ch9/evaluation.py.
"""

# --- Listing 9.1 ---
from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Bid(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", allow_inf_nan=False,
        str_strip_whitespace=True
    )
    vendor: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    baseline_id: str = Field(min_length=1)
    rate_gbp_m2: float = Field(gt=0)
    extras_gbp: float = Field(ge=0)
    lead_weeks: int = Field(ge=0)
    carbon_kg_m2: float | None = Field(ge=0)
    reliability: int = Field(ge=1, le=5)
    supply_risk: int = Field(ge=1, le=5)
    technical_scope: Literal["accepted", "pending", "rejected"]
    quote_ref: str = Field(min_length=1)
    review_ref: str | None = Field(default=None, min_length=1)


# --- Listing 9.2 ---
# Synthetic inputs: replace with controlled, reviewed project exports.
package = {
    "project": "Horizon One Tower",
    "package_id": "HOT-POD-FAC-01",
    "baseline_id": "DEMO-BASELINE-R03",
    "quantity_m2": 1200.0,
    "budget_gbp": 1_050_000.0,
    "max_lead_weeks": 18,
    "quantity_source": "DEMO-QTO-R03",
    "budget_source": "DEMO-COST-R03",
    "price_basis": "GBP excluding VAT; common reviewed scope",
    "lead_basis": "Manufacturing release to site delivery",
    "carbon_basis": "A1-A3; kgCO2e per m2 of equivalent facade scope",
}
columns = (
    "vendor", "rate_gbp_m2", "extras_gbp", "lead_weeks",
    "carbon_kg_m2", "reliability", "supply_risk", "technical_scope"
)
rows = [
    ("A", 760.0, 48_000.0, 20, 85.0, 4, 3, "accepted"),
    ("B", 790.0, 32_000.0, 16, 80.0, 4, 2, "accepted"),
    ("C", 780.0, 34_000.0, 18, 70.0, 3, 3, "accepted"),
    ("D", 730.0, 44_000.0, 16, None, 4, 2, "pending"),
]
bids = [
    Bid(
        **dict(zip(columns, row, strict=True)),
        package_id=package["package_id"],
        baseline_id=package["baseline_id"],
        quote_ref=f"DEMO-QUOTE-{row[0]}-R1",
        review_ref=f"DEMO-REVIEW-{row[0]}-R1",
    )
    for row in rows
]


# --- Listing 9.3 ---
weights = {
    "cost": 0.40, "time": 0.25, "carbon": 0.20,
    "reliability": 0.10, "supply": 0.05,
}
# Each pair is (100-point anchor, zero-point anchor).
anchors = {
    "cost": (900_000.0, package["budget_gbp"]),
    "time": (12.0, float(package["max_lead_weeks"])),
    "carbon": (60.0, 100.0),
}


def lower_is_better(value: float, best: float, worst: float) -> float:
    if worst <= best:
        raise ValueError("Scoring anchors must increase.")
    return max(
        0.0, min(100.0, 100 * (worst - value) / (worst - best))
    )


def evaluate(bid: Bid) -> dict:
    total = package["quantity_m2"] * bid.rate_gbp_m2 + bid.extras_gbp
    flags = []
    if (bid.package_id, bid.baseline_id) != (
        package["package_id"], package["baseline_id"]
    ):
        flags.append("Package or baseline mismatch")
    if bid.technical_scope != "accepted" or not bid.review_ref:
        flags.append("Technical/scope review unresolved")
    if bid.carbon_kg_m2 is None:
        flags.append("Carbon evidence missing")
    if total > package["budget_gbp"]:
        flags.append("Above budget boundary")
    if bid.lead_weeks > package["max_lead_weeks"]:
        flags.append("Beyond delivery window")

    components, score = {}, None
    if not flags:
        components = {
            "cost": lower_is_better(total, *anchors["cost"]),
            "time": lower_is_better(bid.lead_weeks, *anchors["time"]),
            "carbon": lower_is_better(
                bid.carbon_kg_m2, *anchors["carbon"]
            ),
            "reliability": 25.0 * (bid.reliability - 1),
            "supply": 25.0 * (5 - bid.supply_risk),
        }
        score = sum(
            weights[key] * value for key, value in components.items()
        )
    return {
        "vendor": bid.vendor, "total_gbp": total,
        "score": score, "components": components, "flags": flags,
        "quote_ref": bid.quote_ref, "review_ref": bid.review_ref,
    }


matrix = [evaluate(bid) for bid in bids]
ranked = sorted(
    [row for row in matrix if row["score"] is not None],
    key=lambda row: row["score"], reverse=True,
)
for row in matrix:
    row["rank"] = (
        1 + sum(other["score"] > row["score"] for other in ranked)
        if row["score"] is not None else None
    )
    print(row["vendor"], row["total_gbp"], row["score"], row["flags"])


# --- Listing 9.4 ---
review_pack = deepcopy({
    "created_at": datetime.now(timezone.utc).isoformat(),
    "package": package,
    "evaluation_version": "DEMO-EVAL-01",
    "weights": weights,
    "anchors": anchors,
    "inputs": [bid.model_dump() for bid in bids],
    "matrix": matrix,
    "review_status": "awaiting_commercial_review",
    "approved_supplier": None,
})

print(review_pack["review_status"], review_pack["approved_supplier"])
