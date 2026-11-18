"""IFC extraction tool - Chapter 2's "Extracting Horizon One Tower spaces
from IFC" example.

The book's code is:

    import ifcopenshell
    model = ifcopenshell.open("HorizonOne_Architecture.ifc")
    spaces = model.by_type("IfcSpace")
    space_data = []
    for space in spaces:
        space_data.append({
            "ifc_id": space.GlobalId,
            "name": space.Name,
            "type": space.ObjectType,
        })

Chapter 2's own commentary on this example is the design principle for this
whole module: "The language model does not need to interpret the complete
IFC file directly. IFCOpenShell performs the deterministic extraction." So
this function never involves the model core at all - it is pure,
deterministic data extraction, exactly as the book describes.

``ifcopenshell`` is an optional dependency (it is a large native package).
If it is not installed, :func:`extract_spaces` falls back to the pre-computed
extract shipped in ``data/horizon_one_tower/ifc_spaces_extract.json``, which
was generated from the same IFC file by ``scripts/generate_sample_ifc.py``.
Either path returns the same shape, so calling code never needs to know
which one ran.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def extract_spaces(ifc_path: Path | str, fallback_extract: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return ``[{"ifc_id", "name", "type", "storey"}, ...]`` for every
    ``IfcSpace`` in the model at ``ifc_path``.

    Falls back to ``fallback_extract`` (typically
    :meth:`horizon_core.project.HorizonOneTowerProject.ifc_spaces_fallback_extract`)
    if ``ifcopenshell`` cannot be imported, so this always works even on a
    machine where the (large, native) IFC toolchain is not installed.
    """
    try:
        import ifcopenshell
    except ImportError:
        return fallback_extract

    model = ifcopenshell.open(str(ifc_path))
    spaces = model.by_type("IfcSpace")
    space_data = []
    for space in spaces:
        space_data.append(
            {
                "ifc_id": space.GlobalId,
                "name": space.Name,
                "type": space.ObjectType,
                "storey": getattr(space, "LongName", None),
            }
        )
    return space_data
