from collections import defaultdict

groups = defaultdict(list)
for gap in gaps:
    groups[(gap["category"], gap["parameter"])].append(
        gap["object_id"])

for (category, parameter), ids in groups.items():
    print(f"{category}: {parameter} ({len(ids)})")
    print("   ", ", ".join(ids))
