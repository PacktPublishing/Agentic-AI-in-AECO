from horizon_core.context import default_context
from ch3.orchestrator import AECOOrchestrator, DEFAULT_SPECIALISTS
from ch7.agent import CarbonScreeningAgent
from ch8.agent import CostIntelligenceAgent
from appendix_a.end_to_end import GovernedSupplierEvaluation

context = default_context()
specialists = {
    **DEFAULT_SPECIALISTS,
    "carbon": CarbonScreeningAgent,
    "cost_intelligence": CostIntelligenceAgent,
    "supplier_evaluation": GovernedSupplierEvaluation,
}
orchestrator = AECOOrchestrator(
    context, specialists, parallel=True, pause_for_review=True)

paused = orchestrator.run_change_review("DCR-0007")
print(paused["paused_at"], len(paused["findings"]), "findings")

final = orchestrator.record_decision(
    "DCR-0007", approved=False, reviewer="Design Lead",
    comments="Hold: EPD, return-panel rate, FM access.")
print(final["review_status"])
print(len(context.audit_log.entries), "audit entries")
