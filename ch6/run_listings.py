"""The Chapter 6 listings, in order, sharing one namespace.

    python -m ch6.run_listings

Run from the repository root.
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent / "listings"


def main() -> None:
    os.chdir(HERE.parents[1])
    namespace: dict = {"__name__": "ch6_listings"}
    for path in sorted(HERE.glob("l*.py")):
        print(f"--- {path.stem}")
        exec(compile(path.read_text(), str(path), "exec"), namespace)


if __name__ == "__main__":
    main()
