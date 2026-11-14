# Horizon One Tower: companion code for *Agentic AI in AECO*

Runnable Python for every chapter of the book, built around one fictional
project, Horizon One Tower: a 32-storey mixed-use tower with a six-storey
podium in a London regeneration area. One shared dataset and one small agent
framework (`horizon_core/`) support all fifteen chapters, so an agent built
in one chapter can be reused in the next.

Everything runs offline. No API key is needed: a deterministic `MockLLM`
words the findings, and every number is calculated in code. Set
`ANTHROPIC_API_KEY` to use Claude instead, or point the Chapter 14 routes at a
local model with `OllamaLLM`. No agent code changes.

All project data is fictional teaching data. Nothing here is professional
advice, a design value or a recommended setting.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # core: every chapter except 12
pip install -r requirements-full.txt     # adds IfcOpenShell, Open3D and the Appendix A extras

pytest                                    # 125 tests, including every chapter's listings
python -m ch3.run_ch3_demo                # any chapter demo
python -m ch9.listings                    # the code exactly as printed in a chapter
python -m appendix_a.end_to_end           # one design change, agents from six chapters
python -m appendix_a.evaluation           # expected-answer evaluation set
```

## How the code follows the book

Three rules from the chapters run through every module:

1. **Calculations in code, wording by the model.** Quantities, costs, carbon,
   scores, deviations and maturity are computed with pandas, NumPy or
   Open3D. The model only explains results it is given.
2. **Every finding carries its evidence.** Agents return an `AgentFinding`
   with sources, assumptions, risks, confidence and a recommended action.
3. **People decide.** Agents declare what they must not do, name a reviewer
   role, and stop at approval gates. Nothing in this repository approves,
   awards, instructs or writes to a project system.

The book builds one system progressively. Chapter 3's orchestrator is the
shell, and later chapters plug their specialists into it:

```python
from ch3.orchestrator import AECOOrchestrator, DEFAULT_SPECIALISTS
from ch7.agent import CarbonScreeningAgent

orchestrator = AECOOrchestrator(
    context, {**DEFAULT_SPECIALISTS, "carbon": CarbonScreeningAgent},
    parallel=True, pause_for_review=True)
```

## Using the project tools from an AI assistant

The repository includes a read-only MCP server (`appendix_a/mcp_server.py`)
with three tools: open coordination issues, planning constraints and the
façade cost movement. It is already configured for:

- **Claude Code**: `.mcp.json` at the repository root (project scope). Claude
  Code asks you to trust the workspace before the server starts.
- **Gemini CLI**: `.gemini/settings.json`.
- **Any other MCP client**: run `python -m appendix_a.mcp_server` (stdio).

`AGENTS.md` sets out the rules for coding agents working in this repository;
`CLAUDE.md` imports it for Claude Code. See Appendix A, Section A.4.

## Repository layout

```
horizon_core/    shared framework: project data, AgentFinding, BaseAECOAgent (with an
                 automatic agent register), knowledge base, LLM cores, audit log, review gate
data/            Horizon One Tower dataset (JSON, CSV, PDF, IFC, PLY)
ch1/ ... ch15/   one package per chapter
  listings.py    the chapter's code as printed, runnable from the repository root
  agent.py       the chapter's agent, plugged into the shared framework (Chapters 7-14)
  run_chN_demo.py  a demo run (Chapters 1-6 and 15)
appendix_a/      evaluation harness, end-to-end run, untrusted-input screen, tracing, MCP server,
                 and listings/ with every Appendix A listing (python -m appendix_a.listings)
scripts/         generators for every dataset (deterministic)
tests/           one test file per chapter, the appendix, and all listings
docs/            chapter map, review notes for the authors, Appendix A outline
```

`docs/CHAPTER_MAP.md` lists, for each chapter, the listings, modules,
agent, data and the identifiers it shares with other chapters.

## Regenerating the data

```bash
python scripts/generate_sample_pdf.py         # Chapter 2 planning report
python scripts/generate_sample_ifc.py         # Chapter 2 architecture model
python scripts/generate_chapter_data.py       # Chapters 7-15
python scripts/generate_reality_capture.py    # Chapter 12 IFC extract and scan
```

## Licence

Add the licence agreed with the publisher before publishing this repository.
