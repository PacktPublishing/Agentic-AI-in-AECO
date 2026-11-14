# Chapter map

| Ch | Title (short) | Listings | Main modules | Agent(s) | Data |
|---|---|---|---|---|---|
| 1 | Evolution of AI agents | `ch1/simple_agent.py` (Section 1.6) | `coordination_agent.py` | Design Coordination Summary Agent | `issue_log.json`, `rfis.json` |
| 2 | AI-ready data backbone | `ch2/listings.py` | `data_pipeline.py`, `readiness.py` (2.7) | (knowledge base) | `planning_report_P03.pdf`, `HorizonOne_Architecture.ifc` |
| 3 | Multi-agent ecosystems | `ch3/listings.py` | `orchestrator.py` (pluggable, parallel, paused review), `agents.py` | BIM Audit, Cost, Sustainability, Procurement, Planning Risk, Operations | `design_change_requests.json` (DCR-0007), `cost_plan.json` |
| 4 | Feasibility and site intelligence | (no code in text) | `feasibility_agent.py`, `constraint_extraction.py` | Zoning Compliance, GIS, Environmental Risk, Market Intelligence | `planning_policy.json`, `gis_constraints.json` |
| 5 | Generative massing | `ch5/book_listings/` (`python -m ch5.run_listings`); `ch5/listings.py` (scorecard) | `generative_design_agent.py`, `validation_agents.py` | Planning Validation, Structural Feasibility | `massing_brief.json` |
| 6 | BIM auditing | `ch6/listings/` (`python -m ch6.run_listings`) | `audit_agent.py` (incl. Part L limiting-value check) | Audit Agent (BIMGUARD) | `bim_execution_plan.json`, `bim_objects.json`, `facade_document_set.json` |
| 7 | Carbon and materials | `ch7/listings.py` | `carbon.py` | Carbon Screening Agent | `carbon/` |
| 8 | Quantities and cost | `ch8/listings.py` | `cost_demo.py`, `ledger.py` | Cost Intelligence Agent | `cost/` |
| 9 | Procurement | `ch9/listings.py` | `evaluation.py` | Supplier Evaluation Agent | `procurement/` |
| 10 | Planning and progress | `ch10/listings.py` | `progress.py` | Planning and Progress Agent | `programme/` |
| 11 | Robotics and 3D printing | `ch11/listings.py` | `monitoring.py` | Fabrication Monitoring Agent | `fabrication/` |
| 12 | Reality capture and AR | `ch12/listings.py` | `inspection.py` | As-Built Inspection Agent | `reality_capture/` |
| 13 | Facility operations | `ch13/listings.py` | `fm_triage.py` | FM Fault Triage Agent | `operations/` |
| 14 | Governance and trust | `ch14/listings.py` | `governance.py` (`GovernedAgent`) | wraps any agent | `governance/` |
| 15 | Building the agentic AECO enterprise | (no code in text) | `enterprise.py`: use-case screen, pilot decisions, workflow cards, portfolio, skills, roadmap | (portfolio of all agents) | `enterprise/` |
| A | Appendix A | `appendix_a/listings/` (`python -m appendix_a.listings`) | evaluation, end-to-end, untrusted input, tracing, MCP server; `.mcp.json`, `.gemini/settings.json`, `AGENTS.md`, `CLAUDE.md` | - | `golden_cases.json` |

## Shared identifiers

Defined in `data/horizon_one_tower/identifiers.json`.

| Identifier | Meaning | Chapters |
|---|---|---|
| DCR-0007 | Podium façade substitution, ACP to terracotta | 3, 7, 8, 9, Appendix A |
| HOT-POD-FAC-01 | Podium façade package, 1,200 m2 at R03 | 3, 8, 9, 12, 14 |
| L4-CONC / L04-STR | Level 4 concrete activity and zone | 10, 12 |
| SCAN-L04-0428 | Level 4 laser scan, 28 April 2026 | 12 |
| PAV-03 | Pavilion print, third-day lift | 11 |
| H1T-AHU-L19-01 | Air-handling unit (BMS point AHU_19_1, register MEP-AHU-019A) | 13 |
| HOT-GOV-014 | Governed supplier comparison task | 14 |

## Cross-chapter connections in code

- Chapter 12's confirmed issue attaches to Chapter 10's L4-CONC activity (`ch10.progress.apply_spatial_observation`).
- Chapter 14's `GovernedAgent` wraps the Chapter 9 agent; supplier IDs from both chapters are mapped in `governance/source_register.csv`.
- Chapter 15 reads the agent register filled by every chapter's agents.
- `appendix_a/end_to_end.py` runs Chapters 3, 7, 8, 9 and 14 together on DCR-0007.
