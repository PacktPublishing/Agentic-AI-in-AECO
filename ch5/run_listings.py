"""The Chapter 5 listings, in order, sharing one namespace.

    python -m ch5.run_listings

Run from the repository root. ``ch5/listings.py`` holds the Python version
of the chapter's scorecard pseudo-code.
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent / "book_listings"


def main() -> None:
    os.chdir(HERE.parents[1])
    namespace: dict = {"__name__": "ch5_listings"}
    for path in sorted(HERE.glob("l*.py")):
        print(f"--- {path.stem}")
        exec(compile(path.read_text(), str(path), "exec"), namespace)


if __name__ == "__main__":
    main()
