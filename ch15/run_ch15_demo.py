"""Build the Chapter 15 planning artefacts and write them to outputs/ch15.

    python -m ch15.run_ch15_demo
"""
from __future__ import annotations

from pathlib import Path

from horizon_core.project import HorizonOneTowerProject
from ch15.enterprise import (AGENT_REGISTRY, agent_portfolio, governance_maturity, pilot_decisions,
                             roadmap, roadmap_markdown, screen_use_cases, skills_matrix, workflow_card)

OUT = Path(__file__).resolve().parent.parent / "outputs" / "ch15"


def main() -> None:
    p = HorizonOneTowerProject()
    OUT.mkdir(parents=True, exist_ok=True)
    screened = screen_use_cases(p.chapter_csv("enterprise", "use_case_backlog.csv"))
    decisions = pilot_decisions(p.chapter_csv("enterprise", "pilot_results.csv"))
    portfolio = agent_portfolio()
    maturity = governance_maturity(portfolio, p.chapter_json("enterprise", "governance_checklist.json"))
    skills = skills_matrix(p.chapter_csv("enterprise", "skills_survey.csv"))
    plan = roadmap(screened, decisions)

    screened.to_csv(OUT / "use_case_screen.csv", index=False)
    decisions.to_csv(OUT / "pilot_decisions.csv", index=False)
    portfolio.to_csv(OUT / "agent_portfolio.csv", index=False)
    maturity.to_csv(OUT / "governance_maturity.csv", index=False)
    skills.to_csv(OUT / "skills_matrix.csv", index=False)
    (OUT / "roadmap.md").write_text(roadmap_markdown(plan))

    print("Use cases (four criteria and a value measure):")
    for r in screened.itertuples():
        status = "first pilot" if r.first_pilot else "candidate" if r.candidate else f"not ready: {r.missing}"
        print(f"  {r.use_case:<38} {status}")
    print("\nPilot decisions:")
    for r in decisions.itertuples():
        print(f"  {r.use_case:<38} {r.decision:<9} {r.reason}")
    print(f"\n{len(portfolio)} agents in the portfolio")
    print(maturity[["id", "coverage_pct", "control"]].to_string(index=False))
    gaps = skills[skills["gap"] > 0].groupby("skill")["gap"].sum().sort_values(ascending=False)
    print("\nLargest skills gaps:", ", ".join(f"{s} ({g})" for s, g in gaps.head(3).items()))
    card = workflow_card(AGENT_REGISTRY["Design Coordination Summary Agent"])
    print("\nWorkflow card, Design Coordination Summary Agent:")
    for q, a in card.items():
        print(f"  {q} {a}")
    print()
    for step in plan:
        print(f"Months {step['months']}: {step['stage']}")
    print(f"\nFiles written to {OUT}")


if __name__ == "__main__":
    main()
