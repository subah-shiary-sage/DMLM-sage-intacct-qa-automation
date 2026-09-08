"""
Verdict handlers for the depository_category checklist.

No handlers implemented yet — rows are reported as unhandled and left untouched
in the workbook rather than being guessed at. Add handlers with
@registry.sl(...) or @registry.matching(...) as scenarios are automated.
"""

from __future__ import annotations

from . import ScenarioRegistry

registry = ScenarioRegistry("depository_category")
