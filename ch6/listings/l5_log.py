from horizon_core.context import default_context
from ch6.audit_agent import AuditAgent
from ch6.compliance_log import render_compliance_log

agent = AuditAgent(default_context())
log = render_compliance_log(agent.generate_compliance_log())
print(log[["Category", "Severity"]].to_string(index=False))
