"""The Chapter 12 listings, exactly as printed, in chapter order.

    python -m ch12.listings

The listings read their files by name ("HorizonOne_L04_Structure.ifc"),
so this script runs them from data/horizon_one_tower/reality_capture.
Reusable versions are in ch12/inspection.py.
"""
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent / "data" / "horizon_one_tower" / "reality_capture")

# --- Listing 12.1 ---
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import open3d as o3d

model = ifcopenshell.open("HorizonOne_L04_Structure.ifc")
settings = ifcopenshell.geom.settings()
settings.set("use-world-coords", True)

def element_mesh(element):
    shape = ifcopenshell.geom.create_shape(settings, element)
    verts = np.array(shape.geometry.verts).reshape(-1, 3)
    faces = np.array(shape.geometry.faces).reshape(-1, 3)
    mesh = o3d.t.geometry.TriangleMesh(
        o3d.core.Tensor(verts, dtype=o3d.core.float32),
        o3d.core.Tensor(faces, dtype=o3d.core.int32))
    extent = verts.max(axis=0) - verts.min(axis=0)
    return mesh, float(extent[0] * extent[1])

targets = {}
for slab in model.by_type("IfcSlab"):
    mesh, plan_area = element_mesh(slab)
    targets[slab.GlobalId] = {"name": slab.Name,
                              "mesh": mesh,
                              "plan_area_m2": plan_area}

print({t["name"]: round(t["plan_area_m2"], 1)
       for t in targets.values()})


# --- Listing 12.2 ---
import pandas as pd

scan = o3d.io.read_point_cloud("scan_L04_aligned.ply")
points = o3d.core.Tensor(np.asarray(scan.points),
                         dtype=o3d.core.float32)

distances = {}
for guid, target in targets.items():
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(target["mesh"])
    distances[guid] = scene.compute_distance(points).numpy()

d = pd.DataFrame(distances)
assigned = pd.DataFrame({"guid": d.idxmin(axis=1),
                         "dist_m": d.min(axis=1)})
assigned = assigned[assigned["dist_m"] < 0.05]

spec = {
    "surface_position_mm": 10.0,
    "min_coverage": 0.6,
    "design_density_pts_m2": 400,
    "source": "Spec 03-310 cl. 4.2, illustrative values",
}

def assess(guid, group):
    target = targets[guid]
    expected = (target["plan_area_m2"]
                * spec["design_density_pts_m2"])
    coverage = len(group) / expected
    p98_mm = group["dist_m"].quantile(0.98) * 1000
    if coverage < spec["min_coverage"]:
        status = "not assessable"
    elif p98_mm > spec["surface_position_mm"]:
        status = "breach"
    else:
        status = "within tolerance"
    return {"element": target["name"], "guid": guid,
            "points": len(group),
            "coverage": round(coverage, 2),
            "p98_mm": round(p98_mm, 1), "status": status}

results = pd.DataFrame(
    [assess(g, assigned[assigned["guid"] == g])
     for g in targets])
print(results.drop(columns="guid"))


# --- Listing 12.3 ---
import json
import uuid
from datetime import date

capture = {"scan_id": "SCAN-L04-0428",
           "method": "terrestrial laser scan",
           "evidence_tier": 1,
           "registration_rms_mm": 3.0,
           "captured": "2026-04-28"}

def draft_issue(row, capture, spec):
    mesh = targets[row["guid"]]["mesh"]
    centre = mesh.get_center().numpy().round(2).tolist()
    return {
        "topic_guid": str(uuid.uuid4()),
        "title": f"{row['element']}: slab edge outside "
                 "tolerance",
        "topic_type": "Tolerance breach",
        "status": "Draft - awaiting inspector",
        "ifc_guids": [row["guid"]],
        "measurement": {
            "p98_mm": row["p98_mm"],
            "tolerance_mm": spec["surface_position_mm"],
            "coverage": row["coverage"],
            "tolerance_source": spec["source"]},
        "evidence": capture,
        "viewpoint": {"camera_target": centre,
                      "camera_offset_m": [0, -6, 4]},
        "links": {"activity": "L4-CONC", "zone": "L04-STR",
                  "package": "HOT-POD-FAC-01"},
        "created": date.today().isoformat(),
    }

def inspector_decision(issue, confirmed, inspector, note):
    status = "Confirmed" if confirmed else "Closed"
    issue = {**issue, "status": status,
             "inspector": inspector, "inspector_note": note}
    ticket = None
    if confirmed:
        ticket = {
            "ticket": f"RW-{issue['topic_guid'][:8]}",
            "issue": issue["topic_guid"],
            "action": "Survey edge; agree remedial work or "
                      "bracket adjustment",
            "owner": "Frame contractor",
            "status": "Draft - not issued"}
    return issue, ticket

breaches = results[results["status"] == "breach"]
issues = [draft_issue(row, capture, spec)
          for _, row in breaches.iterrows()]
print(json.dumps(issues[0]["measurement"], indent=2))


# --- Listing 12.4 ---
issue, ticket = inspector_decision(
    issues[0], confirmed=True,
    inspector="Site inspector (structures)",
    note="Edge checked by total station at three points: "
         "19 to 23 mm outward.")
print(issue["status"], "|", ticket["status"])
