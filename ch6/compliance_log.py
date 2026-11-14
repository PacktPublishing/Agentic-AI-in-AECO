"""Renders Chapter 6's BIMGUARD compliance log as a table.

Mirrors ``ch5.scorecard``: the log itself
(``ch6.audit_agent.AuditAgent.generate_compliance_log``) is already a list
of structured ``ComplianceLogEntry`` records; this module is purely the
presentation layer, matching the book's own table: Category, Finding,
Source, Severity, Responsible Discipline.
"""
from __future__ import annotations

from typing import List

import pandas as pd

from horizon_core.schemas import ComplianceLogEntry


def render_compliance_log(entries: List[ComplianceLogEntry]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Category": e.category,
                "Finding": e.finding,
                "Source": e.source,
                "Severity": e.severity,
                "Responsible Discipline": e.responsible_discipline,
            }
            for e in entries
        ]
    )


def display_compliance_log(df: pd.DataFrame) -> None:
    with pd.option_context("display.width", 160, "display.max_colwidth", 45):
        print(df.to_string(index=False))
