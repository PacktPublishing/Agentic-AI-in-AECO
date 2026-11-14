"""Generate a small, genuine IFC4 file for Horizon One Tower.

Real projects would export this from Revit/Archicad/etc. Here we build a
minimal but structurally valid IFC file directly with IfcOpenShell so that
``horizon_core.tools.ifc_tools.extract_spaces`` in Chapter 2 has an actual
.ifc file to open with ``ifcopenshell.open(...)`` and ``model.by_type("IfcSpace")``,
matching the book's example exactly, rather than only a cached JSON extract.

Run with:
    python scripts/generate_sample_ifc.py
"""
from __future__ import annotations

import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.guid as guid

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "horizon_one_tower"
OUTPUT_IFC = DATA_DIR / "HorizonOne_Architecture.ifc"
EXTRACT_JSON = DATA_DIR / "ifc_spaces_extract.json"

# A representative (not exhaustive) slice of Horizon One Tower's architectural
# spaces, spanning basement, podium, and tower levels.
SPACES = [
    {"name": "B1-PLANT-01", "type": "Plant Room", "storey": "Basement 1"},
    {"name": "B1-CARPARK-01", "type": "Car Park", "storey": "Basement 1"},
    {"name": "GF-RETAIL-01", "type": "Retail", "storey": "Ground Floor"},
    {"name": "GF-RETAIL-02", "type": "Retail", "storey": "Ground Floor"},
    {"name": "GF-RETAIL-03", "type": "Retail", "storey": "Ground Floor"},
    {"name": "GF-LOBBY-01", "type": "Residential Lobby", "storey": "Ground Floor"},
    {"name": "GF-PUBLICREALM-01", "type": "Public Realm", "storey": "Ground Floor"},
    {"name": "P3-OFFICE-01", "type": "Office", "storey": "Podium Level 3"},
    {"name": "P3-OFFICE-02", "type": "Office", "storey": "Podium Level 3"},
    {"name": "P3-PLANTROOM-01", "type": "Plant Room", "storey": "Podium Level 3"},
    {"name": "T18-RES-01", "type": "Residential Apartment", "storey": "Tower Level 18"},
    {"name": "T18-RES-02", "type": "Residential Apartment", "storey": "Tower Level 18"},
    {"name": "T18-CORE-01", "type": "Core / Circulation", "storey": "Tower Level 18"},
    {"name": "T30-RES-01", "type": "Residential Apartment", "storey": "Tower Level 30"},
    {"name": "T30-AMENITY-01", "type": "Residents Amenity", "storey": "Tower Level 30"},
]


def build_ifc() -> None:
    model = ifcopenshell.file(schema="IFC4")

    # The IfcProject entity anchors the file's schema/units even though we
    # don't reference it again directly - every valid IFC file needs one.
    model.create_entity("IfcProject", GlobalId=guid.new(), Name="Horizon One Tower")

    space_records = []
    for entry in SPACES:
        space = model.create_entity(
            "IfcSpace",
            GlobalId=guid.new(),
            Name=entry["name"],
            ObjectType=entry["type"],
            LongName=entry["storey"],
        )
        space_records.append(
            {
                "ifc_id": space.GlobalId,
                "name": space.Name,
                "type": space.ObjectType,
                "storey": space.LongName,
            }
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    model.write(str(OUTPUT_IFC))
    EXTRACT_JSON.write_text(json.dumps(space_records, indent=2))
    print(f"Wrote {OUTPUT_IFC} with {len(space_records)} IfcSpace entities")
    print(f"Wrote fallback extract to {EXTRACT_JSON}")


if __name__ == "__main__":
    build_ifc()
