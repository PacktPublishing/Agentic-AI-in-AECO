from horizon_core.project import HorizonOneTowerProject
from ch2.data_pipeline import build_knowledge_base

kb = build_knowledge_base(HorizonOneTowerProject())
hits = kb.query("height limit tall buildings", top_k=2,
                status_in=["Approved"])
for record, score in hits:
    print(f"{score:.2f}", record.citation())
