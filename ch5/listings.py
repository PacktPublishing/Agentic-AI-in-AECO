"""Chapter 5 scorecard listing, written in Python.

The chapter shows the scorecard step as pseudo-code. This is the same step
against the generated Horizon One Tower options:

    python -m ch5.listings
"""
from __future__ import annotations

from horizon_core.context import default_context
from ch5.generative_design_agent import generate_horizon_one_tower_options
from ch5.scorecard import generate_scorecard
from ch5.validation_agents import PlanningValidationAgent

# Process: map evaluation metrics to a table
def generate_scorecard_table(option_results):
    data_table = generate_scorecard(option_results)   # 1. structure the raw evaluation data
    return data_table.to_string(index=False)          # 2. render for review


if __name__ == "__main__":
    planning = PlanningValidationAgent(default_context())
    options = [planning.validate(o) for o in generate_horizon_one_tower_options()]
    print(generate_scorecard_table(options))
