"""
conftest.py — Session-wide fixtures shared by every module's tests
(Depository Account Category, Loan Type, ...), plus the failure-reporting
system (screenshots + Markdown/HTML bug reports + JSON summary).

Module-specific fixtures (navigation, "create a test record", etc.) live in
each module's own conftest.py:
  - tests/depository_category/conftest.py
  - tests/loan_type/conftest.py
pytest discovers those automatically for tests under their directory — no
import needed here.

Login + navigation flow verified against the live app on 2026-07-15:
  1. Log in with .env credentials (classic Intacct login form).
  2. Remain at Top level by default. An entity switch occurs only when a Jira
     explicitly requires it and ENTITY_LABEL is set for that run.
  3. Enter the Depository Management module so its top-nav menu is available
     for the initial navigation (individual page objects' navigate_to_list()
     handle switching between the Depository Management and Lending
     Management modules from there — see
     pages/depository_category/listing_page.py / pages/loan_type/listing_page.py).
"""

import sys
import json
import base64
import html as html_lib
import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# ── Root on sys.path so `pages.*` imports work ────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from automation_lib.session import SessionConfig, start_authenticated_session  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# Session-scoped Playwright instance
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def pw():
    """Raw Playwright instance, alive for the whole test session."""
    p = sync_playwright().start()
    yield p
    p.stop()


@pytest.fixture(scope="session")
def authenticated_page(pw):
    """
    Logged-in Sage Intacct page at Top level, Depository Management module active.

    The flow itself lives in automation_lib/session.py so the standalone
    regression runner drives the identical login/entity-switch path.
    """
    session = start_authenticated_session(SessionConfig.from_env(), playwright=pw)
    yield session.page
    session.close()


# ══════════════════════════════════════════════════════════════════════════════
# Reporting — step tracking, bug reports on failure, JSON summary
# ══════════════════════════════════════════════════════════════════════════════

REPORTS_DIR = ROOT / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
BUG_REPORTS_DIR = REPORTS_DIR / "bug_reports"


@pytest.fixture()
def steps() -> list:
    """
    Human-readable step log a test can append to, e.g. ``steps.append("Opened
    Create form")``. Purely optional — tests that don't use it just produce a
    bug report with no recorded steps on failure. Recording steps makes the
    generated bug report (see _bug_report_on_failure below) describe *how* the
    test got to the failure, not just where it stopped.
    """
    return []


def _safe_test_id(nodeid: str) -> str:
    return (
        nodeid.replace("/", "_").replace("\\", "_")
        .replace("::", "__").replace(" ", "_")
    )


def _module_name_from_nodeid(nodeid: str) -> str:
    """
    Derive the module subfolder (e.g. "loan_interest_rate") from a test's
    nodeid, e.g. "tests/loan_interest_rate/test_create.py::Class::test_x" ->
    "loan_interest_rate". Falls back to "misc" for tests directly under
    tests/ with no module subpackage.
    """
    path_part = nodeid.split("::", 1)[0].replace("\\", "/")
    parts = path_part.split("/")
    if len(parts) >= 3 and parts[0] == "tests":
        return parts[1]
    return "misc"


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def _render_bug_report_html(*, title, test_id, status_label, timestamp, duration,
                             current_url, docstring, steps, error_excerpt, screenshot_b64):
    """
    Self-contained HTML bug report: the screenshot is embedded as a base64
    data URI directly in the file (not a separate linked image), so the
    single .html file is everything needed to triage the failure — no
    reports/screenshots/ folder required alongside it.
    """
    esc = html_lib.escape

    steps_html = (
        "<ol>" + "".join(f"<li>{esc(s)}</li>" for s in steps) + "</ol>"
        if steps else "<p><em>No steps were recorded for this test.</em></p>"
    )
    docstring_html = (
        f'<section><h2>What this test verifies</h2><p>{esc(docstring)}</p></section>'
        if docstring else ""
    )
    if screenshot_b64:
        screenshot_html = f'<img src="data:image/png;base64,{screenshot_b64}" alt="failure screenshot">'
    else:
        screenshot_html = "<p><em>Screenshot could not be captured (page already closed).</em></p>"

    status_class = "status-failed" if status_label == "FAILED" else "status-error"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Bug Report — {esc(title)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0;
         padding: 2rem; background: #f6f7f9; color: #1a1a1a; }}
  .card {{ max-width: 960px; margin: 0 auto; background: #fff; border-radius: 8px;
           box-shadow: 0 1px 4px rgba(0,0,0,0.1); padding: 2rem; }}
  h1 {{ font-size: 1.4rem; margin-top: 0; }}
  h2 {{ font-size: 1.05rem; margin-top: 2rem; border-bottom: 1px solid #e2e2e2; padding-bottom: 0.3rem; }}
  .meta {{ list-style: none; padding: 0; margin: 1rem 0; font-size: 0.92rem; }}
  .meta li {{ padding: 0.15rem 0; }}
  .meta b {{ display: inline-block; min-width: 160px; color: #555; }}
  .status-failed {{ color: #b91c1c; font-weight: 600; }}
  .status-error  {{ color: #b45309; font-weight: 600; }}
  pre {{ background: #1e1e1e; color: #eaeaea; padding: 1rem; border-radius: 6px;
         overflow-x: auto; font-size: 0.85rem; white-space: pre-wrap; word-break: break-word; }}
  img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; margin-top: 0.5rem; }}
  code {{ background: #f0f0f0; padding: 0.1rem 0.35rem; border-radius: 3px; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Bug Report — {esc(title)}</h1>
    <ul class="meta">
      <li><b>Test ID</b> <code>{esc(test_id)}</code></li>
      <li><b>Status</b> <span class="{status_class}">{esc(status_label)}</span></li>
      <li><b>Timestamp</b> {esc(timestamp)}</li>
      <li><b>Duration</b> {duration}s</li>
      <li><b>Page URL at failure</b> {esc(current_url)}</li>
    </ul>
    {docstring_html}
    <section>
      <h2>Steps taken</h2>
      {steps_html}
    </section>
    <section>
      <h2>Failure</h2>
      <pre>{esc(error_excerpt)}</pre>
    </section>
    <section>
      <h2>Screenshot</h2>
      {screenshot_html}
    </section>
  </div>
</body>
</html>
"""


@pytest.fixture(autouse=True)
def _bug_report_on_failure(request, authenticated_page, steps):
    """
    On test failure: capture a full-page screenshot, then write both a
    Markdown bug report AND a self-contained HTML bug report
    (reports/bug_reports/<module>/<test_id>.md / .html, screenshot at
    reports/screenshots/<module>/<test_id>.png). The module subfolder (e.g.
    "loan_interest_rate") is derived from the test's own path, so each
    module's failures stay grouped together instead of one flat pile. Both
    reports contain the test's purpose (docstring), the steps recorded via
    the `steps` fixture, and the failure message; the HTML version
    additionally embeds the screenshot in-page as a base64 data URI so that
    single file is everything needed to triage the failure.
    """
    yield
    # A failure can surface on any phase: "call" for an assertion/exception in
    # the test body, or "setup"/"teardown" for a fixture that blew up (e.g. a
    # navigation fixture hitting a closed page) — pytest reports those as
    # "error", not "failed", and only populates rep_setup/rep_teardown, not
    # rep_call. Check all three so setup-phase errors still get a bug report.
    rep = None
    for phase in ("call", "setup", "teardown"):
        candidate = getattr(request.node, f"rep_{phase}", None)
        if candidate and candidate.failed:
            rep = candidate
            break
    if rep is None:
        return

    safe = _safe_test_id(request.node.nodeid)
    module = _module_name_from_nodeid(request.node.nodeid)

    module_screenshots_dir = SCREENSHOTS_DIR / module
    module_screenshots_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = module_screenshots_dir / f"{safe}.png"
    screenshot_bytes = None
    try:
        # Capture once as bytes (not via `path=`) so the same capture can be
        # written to disk AND base64-embedded in the HTML report, rather than
        # taking two separate screenshots that could show different state.
        screenshot_bytes = authenticated_page.screenshot(full_page=True)
        screenshot_path.write_bytes(screenshot_bytes)
    except Exception:
        pass  # page may already be closed — non-fatal

    try:
        current_url = authenticated_page.url
    except Exception:
        current_url = "(unavailable — page closed)"

    docstring = (request.node.function.__doc__ or "").strip() if hasattr(request.node, "function") else ""
    error_text = str(rep.longrepr) if rep.longrepr else "(no error detail captured)"
    # Keep the report readable — the raw pytest traceback can be very long.
    error_lines = error_text.splitlines()
    error_excerpt = "\n".join(error_lines[-40:]) if len(error_lines) > 40 else error_text

    module_bug_reports_dir = BUG_REPORTS_DIR / module
    module_bug_reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    duration = round(getattr(rep, "duration", 0), 3)
    status_label = "FAILED" if rep.when == "call" else f"ERROR ({rep.when} phase)"

    # ── Markdown report ──────────────────────────────────────────────────────
    md_lines = [
        f"# Bug Report — {request.node.name}",
        "",
        f"- **Test ID:** `{request.node.nodeid}`",
        f"- **Status:** {status_label}",
        f"- **Timestamp:** {timestamp}",
        f"- **Duration:** {duration}s",
        f"- **Page URL at failure:** {current_url}",
        "",
    ]
    if docstring:
        md_lines += ["## What this test verifies", "", docstring, ""]

    md_lines += ["## Steps taken", ""]
    if steps:
        md_lines += [f"{i + 1}. {s}" for i, s in enumerate(steps)]
    else:
        md_lines += ["_No steps were recorded for this test._"]
    md_lines += [""]

    md_lines += ["## Failure", "", "```", error_excerpt, "```", ""]

    if screenshot_bytes is not None:
        md_lines += ["## Screenshot", "", f"![failure screenshot](../../screenshots/{module}/{safe}.png)", ""]
    else:
        md_lines += ["## Screenshot", "", "_Screenshot could not be captured (page already closed)._", ""]

    (module_bug_reports_dir / f"{safe}.md").write_text("\n".join(md_lines), encoding="utf-8")

    # ── Self-contained HTML report (screenshot embedded in-page) ───────────────
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii") if screenshot_bytes else None
    html_report = _render_bug_report_html(
        title=request.node.name,
        test_id=request.node.nodeid,
        status_label=status_label,
        timestamp=timestamp,
        duration=duration,
        current_url=current_url,
        docstring=docstring,
        steps=steps,
        error_excerpt=error_excerpt,
        screenshot_b64=screenshot_b64,
    )
    (module_bug_reports_dir / f"{safe}.html").write_text(html_report, encoding="utf-8")


@pytest.hookimpl
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    REPORTS_DIR.mkdir(exist_ok=True)
    stats = terminalreporter.stats
    passed  = len(stats.get("passed",  []))
    failed  = len(stats.get("failed",  []))
    error   = len(stats.get("error",   []))
    skipped = len(stats.get("skipped", []))

    tests = []
    for status in ("passed", "failed", "error", "skipped"):
        for rep in stats.get(status, []):
            entry = {
                "id":       rep.nodeid,
                "status":   status,
                "duration": round(getattr(rep, "duration", 0), 3),
                "message":  str(rep.longrepr) if status in ("failed", "error") else "",
            }
            if status in ("failed", "error"):
                safe = _safe_test_id(rep.nodeid)
                module = _module_name_from_nodeid(rep.nodeid)
                bug_report_md = BUG_REPORTS_DIR / module / f"{safe}.md"
                bug_report_html = BUG_REPORTS_DIR / module / f"{safe}.html"
                if bug_report_md.exists():
                    entry["bug_report"] = str(bug_report_md)
                if bug_report_html.exists():
                    entry["bug_report_html"] = str(bug_report_html)
            tests.append(entry)

    summary = {
        "run_at":  datetime.datetime.now().isoformat(timespec="seconds"),
        "total":   passed + failed + error + skipped,
        "passed":  passed,
        "failed":  failed,
        "errors":  error,
        "skipped": skipped,
        "report":  str(REPORTS_DIR / "report.html"),
        "bug_reports_dir": str(BUG_REPORTS_DIR),
        "tests":   tests,
    }
    (REPORTS_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
