from horizon_core.context import default_context
from ch5.generative_design_agent import (
    generate_horizon_one_tower_options)
from ch5.validation_agents import PlanningValidationAgent

planning = PlanningValidationAgent(default_context())
for option in generate_horizon_one_tower_options():
    planning.validate(option)
    gia = option.gross_internal_area_m2
    gap = gia / target_gia - 1
    print(f"{option.option_id} {gia:>7,.0f} {gap:+6.1%}  "
          f"{option.planning_compliance}")
