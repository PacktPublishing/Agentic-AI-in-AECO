import json
from pathlib import Path

DATA = Path("data/horizon_one_tower")
brief = json.loads((DATA / "massing_brief.json").read_text())

target_gia = sum(brief["target_gia_by_use_m2"].values())
print("Target GIA:", target_gia, "m2")
for name in ("setback_constraint_m", "daylight_threshold",
             "public_realm_min_m2"):
    item = brief[name]
    print(f"{name}: {item['type']}")
    print(f"    source: {item['source']}")
