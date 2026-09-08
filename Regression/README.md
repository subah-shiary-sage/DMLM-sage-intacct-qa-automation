# LME Regression — workflow & conventions

Regression testing of the Sage Intacct Lending modules against
**release.intacct.com (www-p303)**, company `SNL_base_303_M`, entity
**LME – Lending Management Entity**.

Results live in **three** places, and every run updates all three:

| Artifact | What it holds |
|---|---|
| `LME_Regression_Consolidated.xlsx` | The checklist. One sheet per module; the status + evidence note for every scenario. Single source of truth for coverage. |
| JIRA **IADSSL-1714**, comment **4855245** | The running defect list. Append-only, auto-numbered `Bug #N`, every bug with a screenshot. |
| `LME_Regression_Report.html` | Generated summary of the latest run — stat cards, coverage table, executed scenarios, defects. |

## Running a module

```bash
python run_regression.py --list-modules              # what's registered
python run_regression.py --module loan_type --list-rows   # what it would attempt
python run_regression.py --module loan_type --limit 5     # DRY RUN (default)
python run_regression.py --module loan_type --limit 5 --live   # commit for real
```

**Dry run is the default.** Posting to the IADSSL-1714 comment is effectively
irreversible, so `--live` is required to post anything or save the workbook. A
dry run still drives the browser and writes the HTML report, so you can see
exactly what would happen first.

Other flags: `--include-failed` also re-attempts rows already marked `Failed`
(to catch fixes); `--limit N` caps rows per run — worth using on any module's
first live run; `--jira-issue` / `--jira-comment-id` override the configured
target for a one-off.

**Close the workbook in Excel before running.** The script checks for Excel's
lock file up front and stops with a clear message rather than failing after the
browser work is already done.

### Configuration

- `regression_config.yaml` — the module registry: which sheet(s) (and row ranges,
  for the shared `Config Listers` sheet) each module owns, its page objects, and
  its JIRA target. Add a module here, not in Python.
- `.env` — environment and credentials (`APP_URL`, `COMPANY_ID`, `USER_ID`,
  `PASSWORD`, `HEADLESS`, `ENTITY_LABEL`, `MODULE_ENTRY`) plus `JIRA_API_TOKEN`.
  **Never commit the token.** `regression_config.yaml` only names the env var.

## How a verdict is decided

`regression_automation/scenarios/<module>.py` maps a checklist row to a handler
that returns one of:

- **Passed** / **Failed** — the check actually ran and observed the result.
  Only `Failed` with a defect attached ever files a JIRA bug.
- **To be tested** — automation could not confirm the behaviour (selector
  timeout, page misbehaved, prerequisite data missing). Recorded with a note for
  a human. **No bug is filed from this path** — a Playwright exception is an
  automation problem, not evidence of an app defect.
- **Untested** — genuinely not applicable in this environment, with the reason.

Rows with no handler are reported as unhandled and left untouched.

## Checklist workbook layout

Handled by `regression_automation/workbook.py` — don't hardcode row/column
numbers elsewhere. The traps it encodes:

- Two sheet families. CRUD sheets: header row 6, status col 6, comment col 7.
  **`Loan Interest Rate - CRUD` is the exception** — header row 1. Lister/config
  sheets: header row 5, status col 3, comment col 4.
- **Section separators recur throughout a sheet**, not just after the header. A
  row is real data only when its objective cell is non-empty — never assume a
  fixed first-data-row.
- `Loan Type - CRUD` ends with a FINDINGS / EDGE-CASE ADDENDUM narrative block
  (`F1..F12`, `E1`, `E2`, `NOTE`) that is excluded. This exclusion is
  **per-sheet, not global** — `Config Listers` legitimately uses a non-numeric
  SL# (`LT-LISTER-DUPCOL`) for a real row.
- **Stored counts go stale.** Per-sheet header blocks and the Summary table are
  always recomputed from the live status column, never read and trusted.
- The `Jira Bugs` sheet's Bug # column is not reliably an integer (provisional
  rows read like `89 (provisional)`), so numbering coerces and skips non-numerics.

Status values are exactly: `Passed`, `Failed`, `Untested`, `To be tested`.

Evidence notes follow
`EXECUTED <date> (<environment>): <verdict>`, with retests **appended to the
same cell** as `  ||  RETEST (<ticket>, <date>): <verdict>` so prior evidence is
never overwritten.

## Defect filing

A defect found in a run is mirrored into the `Jira Bugs (IADSSL-1714)` sheet
**as soon as it is found**, not held back until it is filed. If filing is
blocked (no token, JIRA down), the row is still written — shaded yellow, numbered
`(pending)`, with the blocker in the Status cell — so the workbook never hides a
known defect.

Bug numbering is anchored to the JIRA comment, not the workbook: the runner
compares the two at startup and refuses to file anything if they've drifted,
rather than guessing.

## Screenshots

Run screenshots land in `Regression/_run_screenshots/`. Every filed defect has
one, embedded in the JIRA comment as `!file.png!`.

---

### Historical: per-page bug reports

Earlier work used one `BR_<Module>_<Page>_<YYYYMMDD>.xlsx` per page under a
per-module folder, with IDs like `LA-CREATE-001` and a
`_templates/BugReport_TEMPLATE.xlsx`. Those files are kept for reference, but
**new work uses the consolidated workbook + the IADSSL-1714 comment above** —
don't create new per-page bug report files.
