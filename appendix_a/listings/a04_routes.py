from horizon_core.llm import MockLLM, OllamaLLM
from ch9.agent import SupplierEvaluationAgent
from ch14.governance import GovernedAgent

routes = {
    "approved_external_ai": MockLLM,
    "enterprise_private_ai": MockLLM,
    "local_private_ai": lambda: OllamaLLM(model="llama3.1"),
}
governed = GovernedAgent(
    SupplierEvaluationAgent(default_context()), routes)
finding = governed.run(
    "Compare façade supplier submissions",
    task_id="HOT-GOV-014", user_role="Commercial Manager",
    action="recommend", source_ids=["SUP-B-RETURN"],
    approved_by="Digital Lead")
print(governed.last_state["route"])
