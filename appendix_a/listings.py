"""The Appendix A listings, in order, sharing one namespace as in a notebook.

    python -m appendix_a.listings

Run from the repository root. Listings A.8 to A.10 need ifctester,
langgraph-checkpoint-sqlite and fastapi (see requirements-full.txt) and
are skipped with a message if those are missing.
"""
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent / "listings"
ROOT = HERE.parents[1]
OPTIONAL = {"a04b_mcp.py": "mcp.types", "a04c_client.py": "mcp.client.stdio", "a08_ids.py": "ifctester",
            "a09_persistence.py": "langgraph.checkpoint.sqlite",
            "a10_service.py": "fastapi"}


def main() -> None:
    namespace: dict = {"__name__": "appendix_a_listings"}
    os.chdir(ROOT)
    workdir = tempfile.mkdtemp()
    for path in sorted(HERE.glob("a*.py")):
        module = OPTIONAL.get(path.name)
        if module:
            try:
                __import__(module)
            except ImportError:
                print(f"--- {path.stem}: skipped (needs {module})")
                continue
        print(f"--- {path.stem}")
        code = path.read_text()
        if path.name == "a09_persistence.py":
            code = code.replace('"reviews.db"',
                                repr(os.path.join(workdir, "reviews.db")))
        exec(compile(code, str(path), "exec"), namespace)


if __name__ == "__main__":
    main()
