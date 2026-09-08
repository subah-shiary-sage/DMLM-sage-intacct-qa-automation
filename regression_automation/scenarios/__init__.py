"""
scenarios — per-module verdict layer.

The runner drives navigation and CRUD generically, but deciding whether a given
checklist row passed is specific to that row's wording, so each module supplies
a small mapping here.

The important rule this layer enforces: a Playwright exception is an *automation*
problem, not evidence of an app defect. Only a scenario that ran and observed
wrong behaviour returns FAILED (and only FAILED results are ever filed as bugs).
Anything unconfirmed returns UNCONFIRMED, which is recorded as "To be tested"
with a note and never becomes a JIRA bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence


class Verdict(str, Enum):
    PASSED = "Passed"
    FAILED = "Failed"
    UNCONFIRMED = "To be tested"
    NOT_APPLICABLE = "Untested"


@dataclass
class Defect:
    """A defect worth filing. Only ever attached to a FAILED outcome."""

    title: str
    area: str
    steps: Sequence[str]
    observed: Sequence[str]
    expected: Sequence[str]
    screenshot: Optional[Path] = None


@dataclass
class Outcome:
    verdict: Verdict
    note: str
    defect: Optional[Defect] = None
    steps: list[str] = field(default_factory=list)

    @classmethod
    def passed(cls, note: str, steps: Sequence[str] = ()) -> "Outcome":
        return cls(Verdict.PASSED, note, steps=list(steps))

    @classmethod
    def failed(cls, note: str, defect: Defect | None = None, steps: Sequence[str] = ()) -> "Outcome":
        return cls(Verdict.FAILED, note, defect=defect, steps=list(steps))

    @classmethod
    def unconfirmed(cls, note: str, steps: Sequence[str] = ()) -> "Outcome":
        return cls(Verdict.UNCONFIRMED, note, steps=list(steps))

    @classmethod
    def not_applicable(cls, note: str, steps: Sequence[str] = ()) -> "Outcome":
        return cls(Verdict.NOT_APPLICABLE, f"N/A - {note}", steps=list(steps))


class ScenarioContext(Protocol):
    """What a scenario handler gets to work with."""

    page: object
    listing_page: object
    record_page: object
    screenshot_dir: Path

    def screenshot(self, name: str) -> Path: ...


# A handler takes (context, checklist_row) and returns an Outcome.
Handler = Callable[[ScenarioContext, object], Outcome]


class ScenarioRegistry:
    """
    Maps checklist rows to handlers.

    Rows are matched by SL# first, then by a case-insensitive substring of the
    objective text — checklist SL#s are not stable across sheet edits, so the
    text fallback keeps a handler attached when rows get renumbered.
    """

    def __init__(self, module: str):
        self.module = module
        self._by_sl: dict[str, Handler] = {}
        self._by_text: list[tuple[str, Handler]] = []

    def sl(self, *sl_numbers: int | str) -> Callable[[Handler], Handler]:
        def decorate(fn: Handler) -> Handler:
            for n in sl_numbers:
                self._by_sl[str(n).strip()] = fn
            return fn

        return decorate

    def matching(self, *needles: str) -> Callable[[Handler], Handler]:
        def decorate(fn: Handler) -> Handler:
            for needle in needles:
                self._by_text.append((needle.lower(), fn))
            return fn

        return decorate

    def resolve(self, row) -> Handler | None:
        if row.sl_no is not None:
            handler = self._by_sl.get(str(row.sl_no).strip())
            if handler:
                return handler
        objective = (row.objective or "").lower()
        for needle, handler in self._by_text:
            if needle in objective:
                return handler
        return None

    def __len__(self) -> int:
        return len(self._by_sl) + len(self._by_text)
