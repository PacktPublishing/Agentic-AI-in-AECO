import json
from pathlib import Path

DATA = Path("data/horizon_one_tower")
bep = json.loads((DATA / "bim_execution_plan.json").read_text())
model = json.loads((DATA / "bim_objects.json").read_text())

for req in bep["requirements"][:4]:
    print(req["object_category"], req["parameter"])
    print("    affects:", ", ".join(req["affects"]))
