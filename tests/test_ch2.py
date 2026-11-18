from __future__ import annotations

from horizon_core.agent_base import AgentContext

from ch2.data_pipeline import build_knowledge_base, demo_query, ingest_architecture_model, ingest_planning_report


def test_ingest_planning_report_returns_tagged_documents(context: AgentContext) -> None:
    docs = ingest_planning_report(context.project)
    assert len(docs) >= 5
    assert any(d.topic == "Height" for d in docs)
    assert all(d.status == "Approved" for d in docs)


def test_ingest_architecture_model_returns_space_documents(context: AgentContext) -> None:
    docs = ingest_architecture_model(context.project)
    assert len(docs) >= 10
    assert all(d.discipline == "Architecture" for d in docs)


def test_build_knowledge_base_and_demo_query(context: AgentContext) -> None:
    kb = build_knowledge_base(context.project)
    assert len(kb) >= 15
    results = demo_query(kb)
    assert results
    top_doc, score = results[0]
    assert top_doc.topic == "Height"
