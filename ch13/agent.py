"""The Chapter 13 FM Fault Triage Agent."""
from __future__ import annotations

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding

from ch13.fm_triage import FMData, triage_hvac_fault


class FMFaultTriageAgent(BaseAECOAgent):
    name = "FM Fault Triage Agent"
    chapter = 13
    reviewer_role = "FM Lead"
    data_class = "confidential"
    purpose = "Triage BMS alarms against asset, maintenance, warranty and O&M records."
    can_do = ["compare telemetry with thresholds", "retrieve O&M guidance with citations", "draft a work order"]
    cannot_do = ["issue a work order", "change BMS setpoints", "authorise component replacement"]

    def run(self, request: str = "AHU_19_1") -> AgentFinding:
        ticket = triage_hvac_fault(FMData(self.context.project), request)
        text = (f"{ticket['asset_id']} ({ticket['location']}): {'; '.join(ticket['evidence']) or 'no threshold exceeded'}. "
                f"Hypothesis: {ticket['working_hypothesis']}. Open tasks: {', '.join(ticket['open_maintenance_tasks']) or 'none'}. "
                f"Warranty {ticket['warranty_status']}: {ticket['warranty_conditions']}.")
        finding = AgentFinding(
            agent=self.name, chapter=13, data_class="confidential",
            finding=self.context.llm.complete("EVIDENCE:\n" + text),
            sources=["bms_iot.csv", "asset_register.csv", "maintenance_history.csv", "warranties.csv"]
                    + ([ticket["om_citation"]] if ticket["om_citation"] else []),
            assumptions=["Average of the last 12 readings (6 hours)"],
            risks=["Warranty conditions restrict who may replace components"],
            confidence="Medium" if len(ticket["evidence"]) == 3 else "Low",
            recommended_action=f"{ticket['recommended_action']} - {ticket['approval_required']} approval required.",
        )
        self.last_ticket = ticket
        self._log(task=f"FM triage {request}", sources=finding.sources,
                  tools_used=["resolve_asset", "recent_average", "retrieve_om_guidance"], output_summary=text)
        return finding
