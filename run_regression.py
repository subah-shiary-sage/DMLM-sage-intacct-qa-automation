#!/usr/bin/env python
"""
run_regression.py — Execute a module's pending regression checklist rows.

    python run_regression.py --module loan_type --limit 5          # dry run (default)
    python run_regression.py --module loan_type --limit 1 --live   # really commit
    python run_regression.py --list-modules
    python run_regression.py --module loan_type --list-rows

Per row it drives the app via that module's page objects, asks the module's
scenario handler for a verdict, writes the result back to the workbook, files
any genuine defect to JIRA, and regenerates the HTML report.

Dry run is the default because a JIRA comment post is effectively irreversible.
``--live`` is required to post anything or save the workbook.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
import traceback
from pathlib import Path

import openpyxl

from automation_lib.session import LoginFailed, SessionConfig, start_authenticated_session
from regression_automation import report as reportmod
from regression_automation import workbook as wbmod
from regression_automation.config import ConfigError, load_config
from regression_automation.jira_client import JiraClient, JiraError
from regression_automation.scenarios import Outcome, Verdict

SCREENSHOT_DIR = Path("Regression/_run_screenshots")

# A crashed tab is recoverable once or twice; beyond that something is
# systematically wrong and continuing would just mass-produce "unconfirmed".
MAX_SESSION_RESTARTS = 3
# Long runs drive dozens of full page loads through one tab; recycling before it
# gets heavy avoids the crash instead of just recovering from it.
RECYCLE_EVERY = 25


class RunContext:
    """What scenario handlers get: the pages, plus screenshot capture."""

    def __init__(self, page, listing_page, record_page, screenshot_dir: Path):
        self.page = page
        self.listing_page = listing_page
        self.record_page = record_page
        self.screenshot_dir = screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def rebind(self, page, listing_page, record_page) -> None:
        self.page = page
        self.listing_page = listing_page
        self.record_page = record_page

    def alive(self) -> bool:
        """False once the browser tab has crashed or closed."""
        try:
            self.page.evaluate("1")
            return True
        except Exception:
            return False

    def reset(self) -> None:
        """Clear leftover dialogs/overlays so each scenario starts clean."""
        if self.record_page is not None:
            self.record_page.reset_ui()
        elif self.listing_page is not None:
            self.listing_page.reset_ui()

    def screenshot(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
        path = self.screenshot_dir / f"{safe}.png"
        self.page.screenshot(path=str(path))
        return path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run LME regression checklist rows for one module.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--module", help="Module key from regression_config.yaml")
    p.add_argument(
        "--live",
        dest="dry_run",
        action="store_false",
        default=True,
        help="Actually post to JIRA and save the workbook (default is a dry run)",
    )
    p.add_argument(
        "--include-failed",
        action="store_true",
        help="Also re-attempt rows already marked Failed (to catch fixes)",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Re-verify EVERY row on the module's sheets, including ones already Passed",
    )
    p.add_argument("--limit", type=int, help="Max rows to attempt this run")
    p.add_argument("--config", type=Path, default=Path("regression_config.yaml"))
    p.add_argument("--report-out", type=Path, default=reportmod.DEFAULT_OUTPUT)
    p.add_argument("--jira-issue", help="Override the configured JIRA issue key")
    p.add_argument("--jira-comment-id", help="Override the configured JIRA comment id")
    p.add_argument("--list-modules", action="store_true", help="List modules and exit")
    p.add_argument(
        "--list-rows",
        action="store_true",
        help="List the rows this module would attempt, then exit (no browser)",
    )
    return p


def _restart_session(session, listing_cls, record_cls, ctx):
    """Close the old session and hand the context a fresh, settled one."""
    try:
        session.close()
    except Exception:
        pass
    new = start_authenticated_session(SessionConfig.from_env())
    listing = listing_cls(new.page) if listing_cls else None
    ctx.rebind(new.page, listing, record_cls(new.page) if record_cls else None)
    new.page.wait_for_timeout(2_000)
    if listing is not None:
        try:
            listing.navigate_to_list()
        except Exception:
            pass
    return new


def _pending_for(wb, module, include_failed: bool, run_all: bool = False):
    rows = []
    for ref in module.sheets:
        if run_all:
            rows.extend(
                wbmod.iter_test_rows(wb, ref.sheet_name, ref.row_start, ref.row_end)
            )
        else:
            rows.extend(
                wbmod.pending_rows(
                    wb,
                    ref.sheet_name,
                    include_failed=include_failed,
                    row_start=ref.row_start,
                    row_end=ref.row_end,
                )
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.list_modules:
        print(f"Modules in {args.config}:\n")
        for name, mod in sorted(cfg.modules.items()):
            runnable = "runnable" if mod.page_object and mod.scenarios else "reporting only"
            sheets = ", ".join(s.sheet_name for s in mod.sheets)
            print(f"  {name:22} [{runnable}]  {sheets}")
            if mod.notes:
                print(f"  {'':22}  note: {mod.notes.strip()}")
        return 0

    if not args.module:
        print("--module is required (or use --list-modules).", file=sys.stderr)
        return 2

    try:
        module = cfg.module(args.module)
    except ConfigError as exc:
        print(f"{exc}", file=sys.stderr)
        return 2

    jira_target = module.jira or cfg.default_jira
    if args.jira_issue:
        jira_target.issue = args.jira_issue
    if args.jira_comment_id:
        jira_target.comment_id = args.jira_comment_id

    workbook_path = cfg.workbook_path
    try:
        wbmod.check_not_locked(workbook_path)
    except wbmod.WorkbookLockedError as exc:
        print(f"{exc}", file=sys.stderr)
        return 3

    wb = openpyxl.load_workbook(workbook_path)
    pending = _pending_for(wb, module, args.include_failed, args.all)
    if args.limit:
        pending = pending[: args.limit]

    if args.list_rows:
        print(f"{len(pending)} row(s) {args.module} would attempt:\n")
        for row in pending:
            print(f"  {row.sheet} row {row.row} SL={row.sl_no} [{row.status}]")
            print(f"      {row.objective[:110]}")
        return 0

    if not module.page_object or not module.scenarios:
        print(
            f"Module {args.module!r} has no page object / scenarios yet, so it cannot "
            f"be executed.\n{module.notes.strip()}\n"
            f"Use --list-rows to see its {len(pending)} pending row(s).",
            file=sys.stderr,
        )
        return 4

    scenarios = module.load_scenarios()
    registry = getattr(scenarios, "registry", None)
    if registry is None:
        print(f"{module.scenarios} defines no 'registry'.", file=sys.stderr)
        return 4

    handled = [(row, registry.resolve(row)) for row in pending]
    runnable = [(row, fn) for row, fn in handled if fn]
    unhandled = [row for row, fn in handled if not fn]

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"[{mode}] module={args.module}  pending={len(pending)}  "
          f"with handlers={len(runnable)}  unhandled={len(unhandled)}")
    if not runnable:
        print("Nothing to execute — no scenario handlers matched the pending rows.")
        _finish(wb, args, module, cfg, [], [], [], unhandled, jira=None)
        return 0

    # Numbering must not drift between JIRA and the workbook mirror.
    jira: JiraClient | None = None
    if not args.dry_run:
        try:
            jira = JiraClient.from_target(jira_target)
            jira_next = jira.next_bug_number_in_comment(
                jira_target.issue, jira_target.comment_id
            )
        except (ConfigError, JiraError) as exc:
            print(f"JIRA setup failed: {exc}", file=sys.stderr)
            return 5
        wb_next = wbmod.next_bug_number(wb)
        if wb_next != jira_next:
            print(
                f"Bug numbering is out of sync: the workbook's next number is {wb_next}, "
                f"JIRA's is {jira_next}.\nReconcile the 'Jira Bugs' sheet against comment "
                f"{jira_target.comment_id} before filing anything new.",
                file=sys.stderr,
            )
            return 6

    executed, defects, unconfirmed = [], [], []
    session = None
    try:
        try:
            session = start_authenticated_session(SessionConfig.from_env())
        except LoginFailed as exc:
            print(f"\n{exc}", file=sys.stderr)
            return 7

        # Record where the run ACTUALLY happened, not where config says it should
        # have. A sandbox result written as if it were release is how a checklist
        # ends up green for a fix that never shipped.
        actual_env = session.describe_environment()
        configured = module.environment or cfg.environment
        run_env = actual_env
        print(f"  environment: {actual_env}")
        host_tokens = [t for t in re.split(r"[\s,]+", configured) if "p3" in t or ".com" in t]
        if host_tokens and not any(h.strip(".") in actual_env for h in host_tokens):
            print(
                f"  ! WARNING: config says {configured!r} but this session is on "
                f"{actual_env!r}.\n"
                f"    Evidence notes will record the ACTUAL environment above.",
                file=sys.stderr,
            )

        listing_cls = module.load_listing_page_object()
        record_cls = module.load_page_object()
        ctx = RunContext(
            session.page,
            listing_cls(session.page) if listing_cls else None,
            record_cls(session.page) if record_cls else None,
            SCREENSHOT_DIR,
        )

        crashes = 0
        for row, handler in runnable:
            label = f"{row.sheet} row {row.row}"

            done = runnable.index((row, handler))
            if done and done % RECYCLE_EVERY == 0 and ctx.alive():
                print(f"  ~ recycling browser session after {done} rows")
                session = _restart_session(session, listing_cls, record_cls, ctx)

            if not ctx.alive():
                crashes += 1
                if crashes > MAX_SESSION_RESTARTS:
                    print(
                        f"  ! browser crashed {crashes} times — stopping rather than "
                        "reporting the rest as unconfirmed.",
                        file=sys.stderr,
                    )
                    for remaining, _ in runnable[runnable.index((row, handler)):]:
                        unconfirmed.append(remaining)
                    break
                print(f"  ~ browser died; restarting session ({crashes})")
                session = _restart_session(session, listing_cls, record_cls, ctx)

            try:
                ctx.reset()
                outcome = handler(ctx, row)
            except Exception as exc:  # noqa: BLE001
                # An automation failure is NOT evidence of an app defect, so this
                # never becomes a filed bug — it's recorded for a human to check.
                outcome = Outcome.unconfirmed(
                    f"Automation could not complete this check: "
                    f"{type(exc).__name__}: {exc}"
                )
                print(f"  ! {label}: automation error — {type(exc).__name__}: {exc}")

            print(f"  - {label}: {outcome.verdict.value}")
            _apply(
                wb, row, outcome, run_env, jira, jira_target,
                args.dry_run, executed, defects, unconfirmed,
            )
    finally:
        if session:
            session.close()

    return _finish(wb, args, module, cfg, executed, defects, unconfirmed, unhandled, jira)


def _apply(wb, row, outcome, run_env, jira, jira_target, dry_run,
           executed, defects, unconfirmed) -> None:
    note = wbmod.evidence_note(outcome.note, environment=run_env, existing=row.comment)

    bug_no: int | str | None = None
    if outcome.verdict is Verdict.FAILED and outcome.defect:
        d = outcome.defect
        if dry_run:
            bug_no = "(dry run)"
        else:
            try:
                bug_no = jira.file_defect(
                    jira_target,
                    area=d.area,
                    title=d.title,
                    steps=d.steps,
                    observed=d.observed,
                    expected=d.expected,
                    screenshot=d.screenshot,
                )
                if wbmod.find_bug_row(wb, bug_no) is None:
                    wbmod.append_bug_row(
                        wb,
                        bug_no=bug_no,
                        module_area=d.area,
                        summary=d.title,
                        related_checklist=f"{row.sheet} row {row.row}",
                    )
                note = f"{note} (Bug #{bug_no})"
            except JiraError as exc:
                # The defect is real even if filing failed — record it in the
                # workbook as pending rather than losing it.
                print(f"    ! JIRA filing failed: {exc}")
                bug_no = "pending"
                wbmod.append_bug_row(
                    wb,
                    bug_no="(pending)",
                    module_area=d.area,
                    summary=d.title,
                    status=f"NOT FILED - {exc}; renumber on filing",
                    related_checklist=f"{row.sheet} row {row.row}",
                    pending=True,
                )
        defects.append(
            {
                "bug_no": bug_no,
                "area": d.area,
                "title": d.title,
                "status": "filed" if isinstance(bug_no, int) else str(bug_no),
                "screenshot": d.screenshot.name if d.screenshot else "",
            }
        )

    wbmod.write_result(wb, row, status=outcome.verdict.value, comment=note)
    row.status, row.comment = outcome.verdict.value, note

    if outcome.verdict is Verdict.UNCONFIRMED:
        unconfirmed.append(row)
    executed.append(row)


def _finish(wb, args, module, cfg, executed, defects, unconfirmed, unhandled, jira) -> int:
    wbmod.recompute_summary(wb)

    notes: list[str] = []
    if unhandled:
        notes.append(
            f"{len(unhandled)} pending row(s) have no scenario handler yet and were "
            f"left untouched — add handlers in {module.scenarios} to automate them."
        )
    if unconfirmed:
        notes.append(
            f"{len(unconfirmed)} row(s) could not be confirmed by automation and are "
            "recorded as 'To be tested' — re-check these by hand."
        )
    if args.dry_run:
        notes.append("This was a dry run: no JIRA posts were made and the workbook was not saved.")

    out = reportmod.generate(
        wb,
        output_path=args.report_out,
        module_name=args.module or "",
        environment_line=module.environment or cfg.environment,
        executed_rows=executed,
        defects=defects,
        skipped=unconfirmed,
        remaining_notes=notes,
        run_timestamp=_dt.datetime.now().isoformat(timespec="seconds"),
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"\nDry run complete. Workbook NOT saved. Report: {out}")
        print("Re-run with --live to commit results and file defects.")
        return 0

    try:
        saved = wbmod.save(wb, cfg.workbook_path)
    except wbmod.WorkbookLockedError as exc:
        print(f"\n{exc}", file=sys.stderr)
        print(f"Report: {out}")
        return 3

    print(f"\nSaved {saved}. Report: {out}")
    print(f"Executed {len(executed)}  defects {len(defects)}  unconfirmed {len(unconfirmed)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
