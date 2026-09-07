#!/usr/bin/env python
"""Run one, several, or all Loan Category tests from a numbered menu.

Every menu entry uses the full-sentence pytest name from ``tests/loan_category``.

Usage:
    python run_loan_category_tests.py
    python run_loan_category_tests.py --list
    python run_loan_category_tests.py --all
    python run_loan_category_tests.py --stage create
    python run_loan_category_tests.py --stage view
    python run_loan_category_tests.py 1
    python run_loan_category_tests.py 1 12 45
    python run_loan_category_tests.py -k document_sequence

Set ``HEADLESS=false`` in ``.env`` to watch the browser. Pytest writes the
HTML and XML reports to the locations configured in ``pytest.ini``.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_ROOT = ROOT / "tests" / "loan_category"
TEST_FILES = (
    "test_create.py",
    "test_view_and_delete.py",
    "test_edit_and_lister.py",
)
STAGES = ("create", "view", "delete", "edit", "list")


@dataclass(frozen=True)
class TestEntry:
    stage: str
    file_name: str
    class_name: str
    function_name: str

    @property
    def nodeid(self) -> str:
        return (
            f"tests/loan_category/{self.file_name}::"
            f"{self.class_name}::{self.function_name}"
        )


def stage_for(file_name: str, class_name: str, function_name: str) -> str:
    if file_name == "test_create.py":
        return "create"
    if class_name == "TestLoanCategoryLister":
        return "list"
    if file_name == "test_edit_and_lister.py":
        return "edit"
    if "delete" in function_name or "deleting" in function_name:
        return "delete"
    return "view"


def discover_tests() -> list[TestEntry]:
    """Read the test source so the menu always matches the collected names."""
    entries: list[TestEntry] = []
    for file_name in TEST_FILES:
        tree = ast.parse((TEST_ROOT / file_name).read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not node.name.startswith("Test"):
                continue
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    entries.append(
                        TestEntry(
                            stage=stage_for(file_name, node.name, child.name),
                            file_name=file_name,
                            class_name=node.name,
                            function_name=child.name,
                        )
                    )
    return entries


def print_menu(tests: list[TestEntry]) -> None:
    current_stage = None
    for number, entry in enumerate(tests, start=1):
        if entry.stage != current_stage:
            current_stage = entry.stage
            print(f"\n-- {current_stage.upper()} --")
        print(f"  {number:>3}. {entry.function_name}")
    print(f"\n{len(tests)} tests total.")


def run(nodeids: list[str], extra_args: list[str]) -> int:
    command = [sys.executable, "-m", "pytest", *nodeids, *extra_args]
    print("Running:", " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    print("\nDone. HTML report: reports\\report.html")
    return result.returncode


def numeric_picks(args: list[str], test_count: int) -> tuple[list[int], list[str]]:
    picks = [int(arg) for arg in args if arg.isdigit()]
    extras = [arg for arg in args if not arg.isdigit()]
    invalid = [pick for pick in picks if not 1 <= pick <= test_count]
    if invalid:
        raise ValueError(f"Test numbers must be between 1 and {test_count}: {invalid}")
    return picks, extras


def main() -> int:
    tests = sorted(discover_tests(), key=lambda entry: STAGES.index(entry.stage))
    args = sys.argv[1:]

    if not args:
        print_menu(tests)
        choice = input("\nEnter test numbers, 'a' for all, or Enter to cancel:\n> ").strip()
        if not choice:
            print("Cancelled.")
            return 0
        if choice.lower() in {"a", "all"}:
            return run([entry.nodeid for entry in tests], [])
        args = choice.split()

    if args[0] == "--list":
        print_menu(tests)
        return 0

    if args[0] == "--all":
        return run([entry.nodeid for entry in tests], args[1:])

    if args[0] == "--stage":
        if len(args) < 2 or args[1] not in STAGES:
            print(f"--stage requires one of: {', '.join(STAGES)}")
            return 1
        selected = [entry.nodeid for entry in tests if entry.stage == args[1]]
        return run(selected, args[2:])

    try:
        picks, extras = numeric_picks(args, len(tests))
    except ValueError as error:
        print(error)
        return 1

    if picks:
        return run([tests[pick - 1].nodeid for pick in picks], extras)

    return run(["tests/loan_category"], extras)


if __name__ == "__main__":
    raise SystemExit(main())
