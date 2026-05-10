"""
Stakeholder reports package.

Keeps backward compatibility with the existing PDF skeleton while adding
the new mapping/renderer flow for stakeolder-specific HTML reports.
"""

from engine.stakeholder_reports.base import ReportKontext, StakeholderReport

REPORT_SCHEMA_VERSION = "1.0.0"

__all__ = ["ReportKontext", "StakeholderReport", "REPORT_SCHEMA_VERSION"]
