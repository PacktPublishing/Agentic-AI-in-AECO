"""Every chapter's listings script must run, so the printed code and the
repository cannot drift apart unnoticed."""
import importlib
import os
import runpy

import pytest

LISTINGS = {
    "ch1.simple_agent": [], "ch6.run_listings": [], "ch5.run_listings": [],
    "ch2.listings": ["fitz"], "ch3.listings": [], "ch5.listings": [], "ch7.listings": [], "ch8.listings": [],
    "ch9.listings": [], "ch10.listings": [], "ch11.listings": [], "ch12.listings": ["open3d", "ifcopenshell"],
    "ch13.listings": [], "ch14.listings": [], "appendix_a.listings": [],
}


@pytest.mark.parametrize("module", sorted(LISTINGS))
def test_listing_runs(module, capsys):
    for dep in LISTINGS[module]:
        try:
            importlib.import_module(dep)
        except ImportError:
            pytest.skip(f"needs {dep}")
    cwd = os.getcwd()
    try:
        runpy.run_module(module, run_name="__main__")
    finally:
        os.chdir(cwd)
    assert capsys.readouterr().out.strip()
