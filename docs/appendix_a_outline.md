# Appendix A: Engineering the Horizon One Tower agent stack

Status: written (Appendix_A_-_Packt_Style.docx). All listings are in
`appendix_a/listings/` and run with `python -m appendix_a.listings`.
The outline below is kept as the section plan.

Purpose: cover the engineering topics the chapters point to but do not have
room for. Each section has runnable code in `appendix_a/` or `horizon_core/`.
Suggested length: 6,000-8,000 words over the sections below.

**A.1 Running the system end to end** (`appendix_a/end_to_end.py`).
One design change reviewed by agents from Chapters 3, 7, 8, 9 and 14: pluggable specialists, parallel execution, the paused approval and one audit trail. Shows how the chapters connect into a single system.

**A.2 Evaluating agents with expected answers** (`appendix_a/evaluation.py`, `golden_cases.json`).
The difference between a test and an evaluation; writing golden cases from reviewed outputs; rerunning after a change of model, prompt, data or library; why a narrative can change while the facts must not; a test that shows a model changing one figure is caught.

**A.3 Model cores and routing** (`horizon_core/llm.py`).
The `LLMClient` protocol; MockLLM for teaching and tests; Claude via the API; a local model via Ollama; mapping Chapter 14 routes to back ends; choosing a model per data class.

**A.4 Connecting tools through MCP** (`appendix_a/mcp_server.py`).
Exposing read-only project tools (issues, constraints, cost movement) to any MCP-capable assistant; why write actions stay behind the governance gate; versioning tool contracts.

**A.5 Tracing and observability** (`appendix_a/tracing.py`).
Spans per agent run with OpenTelemetry; what to record (metadata) and what not to (prompts, confidential text); linking traces to the audit trail.

**A.6 Untrusted input and prompt injection** (`appendix_a/untrusted_input.py`).
Supplier returns, emails and PDFs as data, not instructions; screening; quoting untrusted text in prompts; keeping calculations independent of free text (the Supplier D example); limits of pattern screening.

**A.7 Knowledge base back ends** (`horizon_core/knowledge_base.py`).
TF-IDF for teaching; moving to LlamaIndex with Chroma or pgvector; keeping metadata filters (status, revision) at retrieval time; re-indexing when documents are superseded.

**A.8 Open standards cookbook.**
Short recipes for IDS checks with IfcTester (Chapter 6), writing BCF files (Chapter 12), COBie handover data (Chapter 13) and Brick or Haystack tags for BMS points (Chapter 13).

**A.9 From notebook to service.**
Packaging an agent behind an API, persistence for checkpoints (replacing MemorySaver), configuration, secrets and deployment checks.
