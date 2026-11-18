"""Generate the Chapter 12 IFC extract and synthetic Level 4 scan.

    python scripts/generate_reality_capture.py

Writes data/horizon_one_tower/reality_capture/HorizonOne_L04_Structure.ifc
(three Level 4 slab bays) and scan_L04_aligned.ply (pre-registered synthetic
scan: S1 mostly hidden by stored formwork, S2 façade edge 22 mm outward,
S3 within tolerance). Requires ifcopenshell and numpy.
"""
import os
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "horizon_one_tower" / "reality_capture"
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(OUT)

import ifcopenshell.api as api
import numpy as np
f = api.run("project.create_file")
proj = api.run("root.create_entity", f, ifc_class="IfcProject", name="Horizon One Tower")
api.run("unit.assign_unit", f)
ctx = api.run("context.add_context", f, context_type="Model")
body = api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
bld = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Horizon One Tower")
st = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Level 04")
api.run("aggregate.assign_object", f, relating_object=proj, products=[site])
api.run("aggregate.assign_object", f, relating_object=site, products=[bld])
api.run("aggregate.assign_object", f, relating_object=bld, products=[st])
guids = {"S1":"2N1qr8Hv5Ff9ZLdS0aL04A","S2":"2N1qr8Hv5Ff9ZLdS0aL04B","S3":"2N1qr8Hv5Ff9ZLdS0aL04C"}
for i,(bay,g) in enumerate(guids.items()):
    slab = api.run("root.create_entity", f, ifc_class="IfcSlab", name=f"L04 slab bay {bay}")
    x0=12.0*i
    rep = api.run("geometry.add_slab_representation", f, context=body, depth=0.3,
                  polyline=[(x0,0.0),(x0+12.0,0.0),(x0+12.0,8.0),(x0,8.0)])
    api.run("geometry.assign_representation", f, product=slab, representation=rep)
    api.run("geometry.edit_object_placement", f, product=slab, matrix=np.eye(4))
    api.run("spatial.assign_container", f, relating_structure=st, products=[slab])
    slab.GlobalId = g
f.write("HorizonOne_L04_Structure.ifc"); print("ok")


rng = np.random.default_rng(12)
DENSITY = 400


def top_face(x0, x1):
    n = int((x1 - x0) * 8 * DENSITY)
    x = rng.uniform(x0, x1, n)
    y = rng.uniform(0, 8, n)
    return np.c_[x, y, np.full(n, 0.3)]


def facade_edge(x0, x1, offset_m=0.0):
    n = int((x1 - x0) * 0.3 * DENSITY)
    x = rng.uniform(x0, x1, n)
    z = rng.uniform(0, 0.3, n)
    return np.c_[x, np.full(n, 8.0 + offset_m), z]


s1 = top_face(0, 12)
s1 = s1[s1[:, 0] < 2.4]
s2 = np.r_[top_face(12, 24), facade_edge(12, 24, offset_m=0.022)]
s3 = np.r_[top_face(24, 36), facade_edge(24, 36)]
points = np.r_[s1, s2, s3]
points = points + rng.normal(0, 0.002, points.shape)

with open("scan_L04_aligned.ply", "w") as fh:
    fh.write("ply\nformat ascii 1.0\n")
    fh.write(f"element vertex {len(points)}\n")
    fh.write("property float x\nproperty float y\nproperty float z\nend_header\n")
    np.savetxt(fh, points, fmt="%.4f")
print(len(points), "points written")
