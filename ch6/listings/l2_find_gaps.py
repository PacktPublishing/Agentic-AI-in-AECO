COLLECTIONS = {"Door": "doors", "Wall": "walls",
               "Mechanical Asset": "mechanical_assets",
               "Room": "rooms"}


def is_gap(parameter, value):
    if parameter == "accessibility_clearance_confirmed":
        return value is False
    return value is None or value == "PLACEHOLDER"


def find_gaps(model, requirements):
    gaps = []
    for req in requirements:
        objects = model[COLLECTIONS[req["object_category"]]]
        for obj in objects:
            if req.get("applies_to") and not obj.get(
                    "accessible_facility"):
                continue
            value = obj.get(req["parameter"])
            if is_gap(req["parameter"], value):
                gaps.append({"object_id": obj["object_id"],
                             "category": req["object_category"],
                             "parameter": req["parameter"],
                             "affects": req["affects"]})
    return gaps


gaps = find_gaps(model, bep["requirements"])
print(len(gaps), "gaps")
for gap in gaps[:4]:
    print(gap["object_id"], gap["parameter"])
