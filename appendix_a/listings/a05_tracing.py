from appendix_a.tracing import SPANS, traced

agent = traced(CarbonScreeningAgent(default_context()))
agent.run("DCR-0007")
for key, value in SPANS[-1].items():
    print(f"{key}: {value}")
