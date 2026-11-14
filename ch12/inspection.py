"""Chapter 12: scan-vs-BIM deviation per element, as reusable functions.

Requires ifcopenshell and open3d (``pip install -r requirements-full.txt``).
"""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd

SPEC = {"surface_position_mm": 10.0, "min_coverage": 0.6, "design_density_pts_m2": 400,
        "source": "Spec 03-310 cl. 4.2, illustrative values"}
CAPTURE = {"scan_id": "SCAN-L04-0428", "method": "terrestrial laser scan", "evidence_tier": 1,
           "registration_rms_mm": 3.0, "captured": "2026-04-28"}


def load_targets(ifc_path) -> dict:
    import ifcopenshell
    import ifcopenshell.geom
    import open3d as o3d

    model = ifcopenshell.open(str(ifc_path))
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    targets = {}
    for slab in model.by_type("IfcSlab"):
        shape = ifcopenshell.geom.create_shape(settings, slab)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces = np.array(shape.geometry.faces).reshape(-1, 3)
        mesh = o3d.t.geometry.TriangleMesh(o3d.core.Tensor(verts, dtype=o3d.core.float32),
                                           o3d.core.Tensor(faces, dtype=o3d.core.int32))
        extent = verts.max(axis=0) - verts.min(axis=0)
        targets[slab.GlobalId] = {"name": slab.Name, "mesh": mesh, "plan_area_m2": float(extent[0] * extent[1])}
    return targets


def assess_scan(targets: dict, ply_path, spec: dict = SPEC) -> pd.DataFrame:
    import open3d as o3d

    scan = o3d.io.read_point_cloud(str(ply_path))
    points = o3d.core.Tensor(np.asarray(scan.points), dtype=o3d.core.float32)
    distances = {}
    for guid, t in targets.items():
        scene = o3d.t.geometry.RaycastingScene()
        scene.add_triangles(t["mesh"])
        distances[guid] = scene.compute_distance(points).numpy()
    d = pd.DataFrame(distances)
    assigned = pd.DataFrame({"guid": d.idxmin(axis=1), "dist_m": d.min(axis=1)})
    assigned = assigned[assigned["dist_m"] < 0.05]
    rows = []
    for guid, t in targets.items():
        group = assigned[assigned["guid"] == guid]
        coverage = len(group) / (t["plan_area_m2"] * spec["design_density_pts_m2"])
        p98 = group["dist_m"].quantile(0.98) * 1000
        status = ("not assessable" if coverage < spec["min_coverage"]
                  else "breach" if p98 > spec["surface_position_mm"] else "within tolerance")
        rows.append({"element": t["name"], "guid": guid, "points": len(group), "coverage": round(coverage, 2),
                     "p98_mm": round(p98, 1), "status": status})
    return pd.DataFrame(rows)


def draft_issue(row, targets: dict, capture: dict = CAPTURE, spec: dict = SPEC) -> dict:
    centre = targets[row["guid"]]["mesh"].get_center().numpy().round(2).tolist()
    return {"topic_guid": str(uuid.uuid4()), "title": f"{row['element']}: slab edge outside tolerance",
            "topic_type": "Tolerance breach", "status": "Draft - awaiting inspector", "ifc_guids": [row["guid"]],
            "measurement": {"p98_mm": row["p98_mm"], "tolerance_mm": spec["surface_position_mm"],
                            "coverage": row["coverage"], "tolerance_source": spec["source"]},
            "evidence": capture, "viewpoint": {"camera_target": centre, "camera_offset_m": [0, -6, 4]},
            "links": {"activity": "L4-CONC", "zone": "L04-STR", "package": "HOT-POD-FAC-01"},
            "created": date.today().isoformat()}


def inspector_decision(issue: dict, confirmed: bool, inspector: str, note: str):
    issue = {**issue, "status": "Confirmed" if confirmed else "Closed", "inspector": inspector,
             "inspector_note": note}
    ticket = None
    if confirmed:
        ticket = {"ticket": f"RW-{issue['topic_guid'][:8]}", "issue": issue["topic_guid"],
                  "action": "Survey edge; agree remedial work or bracket adjustment",
                  "owner": "Frame contractor", "status": "Draft - not issued"}
    return issue, ticket
