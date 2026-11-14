doc_set = json.loads(
    (DATA / "facade_document_set.json").read_text())
sources = ["specification", "drawing", "model"]
values = {s: doc_set[s]["value"] for s in sources}
newest = max(sources, key=lambda s: doc_set[s]["date"])
limit = doc_set["regulatory_limit"]["value"]

print("Values:", values)
print("Consistent:", len(set(values.values())) == 1)
print("Newest source:", newest, values[newest])
above = [s for s in sources if values[s] > limit]
print(f"Above the {limit} W/m2K limit:", above or "none")
