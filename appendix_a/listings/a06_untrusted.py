import pandas as pd

from appendix_a.untrusted_input import screen_text, wrap_as_data

bids = pd.read_csv(
    "data/horizon_one_tower/procurement/bids.csv")
for vendor, note in zip(bids["vendor"], bids["supplier_note"]):
    result = screen_text(note)
    print(vendor, "safe" if result.safe else "withheld:")
    for reason in result.reasons:
        print("  -", reason)

print(wrap_as_data("SUP-B-RETURN", bids.at[1, "supplier_note"]))
