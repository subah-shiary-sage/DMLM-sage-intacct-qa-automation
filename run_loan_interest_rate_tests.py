#!/usr/bin/env python
"""Run individual Loan Interest Rate tests from a numbered menu.

Usage:
    python run_loan_interest_rate_tests.py
    python run_loan_interest_rate_tests.py --list
    python run_loan_interest_rate_tests.py --all
    python run_loan_interest_rate_tests.py --stage assignment
    python run_loan_interest_rate_tests.py 1 44 93
    python run_loan_interest_rate_tests.py -k start_date
"""

from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_ROOT = ROOT / "tests" / "loan_interest_rate"
TEST_FILES = (
    "test_list.py",
    "test_create.py",
    "test_validation.py",
    "test_view_and_delete.py",
    "test_edit.py",
    "test_assignment_rules.py",
    "test_schedule_and_blocked.py",
)
STAGES = ("list", "create", "validation", "view", "delete", "edit", "assignment", "blocked")


@dataclass(frozen=True)
class TestEntry:
    stage: str
    file_name: str
    class_name: str
    function_name: str

    @property
    def nodeid(self) -> str:
        return f"tests/loan_interest_rate/{self.file_name}::{self.class_name}::{self.function_name}"


def stage_for(file_name: str, class_name: str, function_name: str) -> str:
    if file_name == "test_list.py":
        return "list"
    if file_name == "test_create.py":
        return "create"
    if file_name == "test_validation.py":
        return "validation"
    if file_name == "test_edit.py":
        return "edit"
    if file_name == "test_assignment_rules.py":
        return "assignment"
    if file_name == "test_view_and_delete.py":
        return "delete" if "delete" in class_name.lower() else "view"
    if class_name.startswith("TestBlocked"):
        return "blocked"
    return "create"


def discover_tests() -> list[TestEntry]:
    entries: list[TestEntry] = []
    for file_name in TEST_FILES:
        tree = ast.parse((TEST_ROOT / file_name).read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not node.name.startswith("Test"):
                continue
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    entries.append(TestEntry(
                        stage_for(file_name, node.name, child.name),
                        file_name,
                        node.name,
                        child.name,
                    ))
    return sorted(entries, key=lambda entry: STAGES.index(entry.stage))


def print_menu(tests: list[TestEntry]) -> None:
    current = None
    for number, entry in enumerate(tests, start=1):
        if entry.stage != current:
            current = entry.stage
            print(f"\n-- {current.upper()} --")
        print(f"  {number:>3}. {entry.function_name}")
    print(f"\n{len(tests)} tests total.")


def run(nodeids: list[str], extra_args: list[str]) -> int:
    command = [sys.executable, "-m", "pytest", *nodeids, *extra_args]
    print("Running:", " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    print("\nDone. HTML report: reports\\report.html")
    return result.returncode


def main() -> int:
    tests = discover_tests()
    args = sys.argv[1:]
    if not args:
        print_menu(tests)
        choice = input("\nEnter test numbers, 'a' for all, or Enter to cancel:\n> ").strip()
        if not choice:
            return 0
        args = ["--all"] if choice.lower() in {"a", "all"} else choice.split()

    if args[0] == "--list":
        print_menu(tests)
        return 0
    if args[0] == "--all":
        return run([entry.nodeid for entry in tests], args[1:])
    if args[0] == "--stage":
        if len(args) < 2 or args[1] not in STAGES:
            print(f"--stage requires one of: {', '.join(STAGES)}")
            return 1
        return run([entry.nodeid for entry in tests if entry.stage == args[1]], args[2:])

    picks = [int(arg) for arg in args if arg.isdigit()]
    extras = [arg for arg in args if not arg.isdigit()]
    invalid = [pick for pick in picks if not 1 <= pick <= len(tests)]
    if invalid:
        print(f"Test numbers must be between 1 and {len(tests)}: {invalid}")
        return 1
    if picks:
        return run([tests[pick - 1].nodeid for pick in picks], extras)
    return run(["tests/loan_interest_rate"], extras)


if __name__ == "__main__":
    raise SystemExit(main())
