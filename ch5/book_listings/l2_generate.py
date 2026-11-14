from ch5.generative_design_agent import generate_variation

option_b = generate_variation(
    option_id="B", label="Stepped podium, slim tower",
    tower_footprint_m2=1550, podium_footprint_m2=3000,
    setback_strategy="3m stepped setback above the podium",
    podium_setback_m=3.0, storeys=30, core_count=1,
    requires_transfer_structure=False,
    floorplate_regularity="regular")

print(option_b.gross_internal_area_m2, option_b.plot_efficiency)
print(option_b.daylight_impact)
clearance = option_b.notes[0].rsplit(" ", 1)[-1]
print("Daylight clearance to Canal Walk Residences:", clearance)
