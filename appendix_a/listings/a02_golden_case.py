import json
from pathlib import Path

path = Path("appendix_a/golden_cases.json")
cases = json.loads(path.read_text())
print(json.dumps(cases[3], indent=2))
