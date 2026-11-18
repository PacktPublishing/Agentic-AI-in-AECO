from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

app = FastAPI()
service = AECOOrchestrator(default_context(),
                           pause_for_review=True,
                           checkpointer=saver)


class Decision(BaseModel):
    approved: bool
    reviewer: str
    comments: str = ""


@app.post("/reviews/{request_id}")
def start_review(request_id: str):
    state = service.run_change_review(request_id)
    return {"paused_at": state.get("paused_at"),
            "route": state["route"]}


@app.post("/reviews/{request_id}/decision")
def decide(request_id: str, decision: Decision):
    state = service.record_decision(
        request_id, decision.approved, decision.reviewer,
        decision.comments)
    return {"status": state["review_status"]}


client = TestClient(app)
print(client.post("/reviews/DCR-0007").json())
print(client.post("/reviews/DCR-0007/decision",
                  json={"approved": True,
                        "reviewer": "Design Lead"}).json())
