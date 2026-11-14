import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

connection = sqlite3.connect("reviews.db",
                             check_same_thread=False)
saver = SqliteSaver(connection)

first = AECOOrchestrator(default_context(),
                         pause_for_review=True,
                         checkpointer=saver)
first.run_change_review("DCR-0007", thread_id="dcr-0007")

later = AECOOrchestrator(default_context(),
                         pause_for_review=True,
                         checkpointer=saver)
result = later.record_decision(
    "DCR-0007", approved=False, reviewer="Design Lead",
    thread_id="dcr-0007")
print(result["review_status"])
