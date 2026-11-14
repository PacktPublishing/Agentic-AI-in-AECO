"""Chapter 5's ``GenerateScorecard`` pseudocode, made runnable.

The book's pseudocode:

    FUNCTION GenerateScorecard(option_results):
        // 1. Structure the raw evaluation data
        data_table = INITIALIZE_TABLE_FROM(option_results)
        // 2. Render to interface
        DISPLAY_TABLE(data_table, settings={full_width: True})

"Using a library like Pandas to aggregate the results and Streamlit to
render them allows the design team to instantly compare options." This
module does the Pandas half directly; :func:`display_scorecard` stands in
for the Streamlit half with a plain-text render, since this codebase has no
UI layer of its own - swap it for ``st.dataframe(df, use_container_width=True)``
in an actual Streamlit app without touching :func:`generate_scorecard`.
"""
from __future__ import annotations

from typing import List

import pandas as pd

from horizon_core.schemas import MassingOption


def generate_scorecard(options: List[MassingOption]) -> pd.DataFrame:
    """Structure massing option results into a comparison table."""
    return pd.DataFrame(
        [
            {
                "Option": o.option_id,
                "Label": o.label,
                "Plot Efficiency": o.plot_efficiency,
                "Daylight to Neighbours": o.daylight_impact,
                "Planning Compliance": o.planning_compliance,
                "Embodied Carbon Direction": o.embodied_carbon_direction,
                "Structural Practicality": o.structural_practicality,
                "GIA (sqm)": o.gross_internal_area_m2,
            }
            for o in options
        ]
    ).set_index("Option")


def display_scorecard(df: pd.DataFrame) -> None:
    """Stand-in for ``DISPLAY_TABLE(data_table, settings={full_width: True})``."""
    with pd.option_context("display.width", 160, "display.max_colwidth", 40):
        print(df.to_string())
