import ifcopenshell
from ifctester import ids, reporter

model = ifcopenshell.open(
    "data/horizon_one_tower/HorizonOne_Architecture.ifc")

named = ids.Specification(name="Spaces are named and typed",
                          ifcVersion=["IFC4"])
named.applicability.append(ids.Entity(name="IFCSPACE"))
named.requirements.append(ids.Attribute(name="Name"))
named.requirements.append(ids.Attribute(name="ObjectType"))

area = ids.Specification(name="Spaces carry a planned area",
                         ifcVersion=["IFC4"])
area.applicability.append(ids.Entity(name="IFCSPACE"))
area.requirements.append(ids.Property(
    propertySet="Pset_SpaceCommon",
    baseName="NetPlannedArea"))

eir = ids.Ids(title="Horizon One Tower EIR checks")
eir.specifications.extend([named, area])
eir.validate(model)
for spec in eir.specifications:
    status = "pass" if spec.status else "fail"
    print(f"{spec.name}: {status}")
