"""GIS query tool.

Chapter 2: "For the agent to use this information, the spatial data must be
queryable and connected to the project context... turning spatial and cost
information into clean, queryable tables or linked records that an LLM can
retrieve, compare, and explain without guessing."

A full GeoPandas/PostGIS stack is overkill for a single fictional site
boundary, and would add a heavy native dependency (GDAL) for no real
benefit here. Horizon One Tower's site constraints are already a small,
simplified set of layers (see ``data/horizon_one_tower/gis_constraints.json``),
so this module just exposes them as plain, queryable Python functions -
which is exactly the destination Chapter 2 describes ("clean, queryable
tables"), regardless of which spatial engine produced them upstream.
"""
from __future__ import annotations

from typing import Any, Dict, List


def flood_risk_summary(gis: Dict[str, Any]) -> str:
    zone = gis["flood_risk"]["zone"]
    notes = gis["flood_risk"]["notes"]
    return f"{zone}. {notes}"


def neighbouring_residential_receptors(gis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Neighbouring buildings with a residential use - the daylight/
    overshadowing "sensitive receptors" an Environmental Risk Agent cares about."""
    return [b for b in gis["neighbouring_buildings"] if b["use"] == "Residential"]


def servicing_conflicts(gis: Dict[str, Any]) -> str:
    return gis["transport"]["servicing_route_conflict"]


def height_context(gis: Dict[str, Any]) -> Dict[str, Any]:
    """Neighbouring building heights and protected-view sensitivity, used to
    cross-reference against the planning height constraint (Chapter 4's
    "Connecting GIS and Environmental Data" section)."""
    return {
        "neighbouring_heights": [
            {"name": b["name"], "storeys": b["storeys"]} for b in gis["neighbouring_buildings"]
        ],
        "within_townscape_sensitivity_area": gis["protected_views"]["affects_height"],
    }
