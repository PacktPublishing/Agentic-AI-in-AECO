"""Run Chapter 2's data pipeline and worked query against Horizon One Tower.

    python -m ch2.run_ch2_demo
"""
from __future__ import annotations

from horizon_core.project import HorizonOneTowerProject

from ch2.data_pipeline import build_knowledge_base, demo_query


def main() -> None:
    project = HorizonOneTowerProject()
    kb = build_knowledge_base(project)
    print(f"Knowledge base built: {len(kb)} documents ingested.\n")

    question = "What constraints could affect Horizon One Tower's height?"
    print(f'Query: "{question}"\n')
    for doc, score in demo_query(kb, question):
        print(f"[{score:.3f}] {doc.topic:<24} {doc.citation()}")
        snippet = " ".join(doc.text.split())[:160]
        print(f"          {snippet}...\n")


if __name__ == "__main__":
    main()
