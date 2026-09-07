---
name: client-test-case-workbook
description: >
  Generate or update the detailed client-facing Sage Intacct test-case workbook (currently
  `Test_Cases_and_Checklists/SNL Test cases.xlsx`): one sheet per module/feature, each with a
  10-column test-case table (Test Case ID, Test Scenario, Preconditions, Test Data, Test Steps,
  Expected Result, Requirement/Jira Reference, IS Automated, Status, Comments), rows grouped under
  colored CREATE/EDIT/VIEW/DELETE heading bands, and a Summary rollup sheet with live COUNTA/COUNTIF
  formulas. Distinct from [[qa-checklist-workbook]] (the simpler SL#/Test Objective/Status format) —
  use this skill when the user references "SNL Test cases.xlsx", asks to add a new sheet/module,
  add field validations, add CRUD sections, or audit Create/Edit coverage on that workbook.
---

# Client test-case workbook format

Builds/updates the single consolidated workbook `Test_Cases_and_Checklists/SNL Test cases.xlsx`
(29 sheets as of 2026-08-27: `Summary` + ~15 `LME *` Lending Management sheets + ~10 `DMS *`
Depository Management sheets). Always work with **openpyxl** directly against this file — never
hand-author markdown, and never create a parallel workbook when the request is "add to" or "update"
existing coverage.

## Sheet anatomy (row-by-row, 1-indexed)

- **A1:J1** merged — sheet title, bold white on dark navy (`1F4E78`), e.g. "Depository - Deposits".
- **A2:B3** merged — "Common Preconditions" label, bold, light-blue fill (`D9EAF7`).
- **C2:J3** merged — the 5 standard preconditions (signed in, correct entity selected, module
  enabled, user has permission, master/config records active), wrap text, `F2F6FB` fill.
- **A4:J4** merged, italic — navigation caption in the exact format:
  `Navigation: <Applications > Module > Page path> | Client baseline | <N> test cases | Updated <ISO date>`
- **Row 5** — blank spacer.
- **Row 6** — column headers, bold white on `1F4E78`, wrap text: Test Case ID, Test Scenario,
  Preconditions, Test Data, Test Steps, Expected Result, Requirement/Jira Reference, IS Automated,
  Status, Comments.
- **Row 7+** — CRUD heading bands and data rows (see below).

Column widths: A=18, B=40, C=38, D=34, E=58, F=48, G=32, H=15, I=16, J=34.

## CRUD heading bands

Every sheet's data rows are grouped under four bold, merged (`A:J`) heading-band rows, in this
fixed order: **CREATE** (green `2E7D32`) → **EDIT** (amber `B8860B`) → **VIEW** (blue `1F4E78`) →
**DELETE** (red `B71C1C`). Band text reads `"<BUCKET>  (<N> test case<s>)"` (singular "test case"
when N=1 — do not hardcode plural). Every row belongs to exactly one bucket; there is no 5th
catch-all — force borderline rows into the closest bucket (field-validation/mandatory/boundary
checks default to CREATE unless the row explicitly says "on Edit"/"on Update").

A handful of sheets are dashboards/report/action pages, not CRUD forms, and are intentionally left
**without** band splitting: `LME Workbench`, `LME Ledger Report`, `LME Roll Forward`, `LME AR
Payment`. Don't force CRUD bands onto a new sheet unless it's a genuine record-management form.

### Test Case ID convention
Short prefix + zero-padded sequence, e.g. `DMS-DEP-001`, `LME-LC-047`. The sequence is
**continuous across all four buckets on a sheet** — it does NOT restart at 1 per bucket. When
inserting/removing rows, renumber every ID on the sheet in bucket order (CREATE, then EDIT, then
VIEW, then DELETE).

## Row content conventions

- **Preconditions (col C)**: `"Refer to Common Preconditions above."` plus one short extra clause
  only when the scenario needs something beyond the common 5 (e.g. "An existing unposted record is
  available to edit." for Edit-bucket rows, or a specific record state for a business-rule check).
- **Test Data (col D)**: newline-separated `Field: Value` pairs with concrete sample values
  (`QA-###`-style IDs), parameterized to the specific check (blank the field being tested, show
  the boundary value, name the specific dropdown-content states involved).
- **Test Steps (col E)**: fixed 6-step pattern — steps 1/2/5/6 are boilerplate, reused verbatim
  across every row on a sheet (only the module path in step 2 changes per sheet):
  ```
  1. Sign in to Sage Intacct with the test user.
  2. Navigate to <Applications > Module > Page>.
  3. Prepare the test data: <specific setup for this scenario>.
  4. <the specific action under test>.
  5. Submit, post, run, or confirm the action as applicable.
  6. Review the confirmation, record, balances, accounting entries, and related history applicable to this scenario.
  ```
- **Expected Result (col F)**: a direct assertion of correct behavior, not "Verify that X" —
  state the outcome ("Submission is blocked and a field-level required message is shown for
  Customer.") rather than the instruction to check it.
- **Requirement/Jira Reference (col G)**: `"<Feature> client requirement; Jira reference TBD"`,
  identical across every row on a sheet.
- **IS Automated (col H)**: `"TBD"`. **Status (col I)**: `"Not Executed"`. New/added rows always
  reset to these defaults regardless of any prior execution history in a source file.
- **Comments (col J)**: blank by default. Use it for (a) internal-implementation-detail notes when
  a check can't be verified purely through the UI (e.g. "Internal reference: verify via
  SNLLOANTXN/SNLLOANINVOICE if backend access is available; otherwise confirm via the posted
  record's accounting entries in the UI."), or (b) policy-dependent flags needing client
  confirmation, or (c) when converting a prior QA checklist, the source's original
  Result/Remarks/bug-ID for traceability (e.g. `"Source reference: 1710 | Prior checklist result:
  Fail | Remarks: Bug #09 - cell goes blank..."`).

## Data validations

Two list-type `DataValidation`s per sheet, applied **only to the data-row ranges within each
bucket** (never across the band rows):
- Column H: `formula1='"Yes,No,Partial,Planned,TBD"'`
- Column I: `formula1='"Not Executed,In Progress,Passed,Failed,Blocked,Not Applicable"'`

When rows are added/removed, always rebuild both validations from scratch
(`ws.data_validations.dataValidation = []` then re-add) covering the *current* per-bucket ranges —
don't try to patch existing ranges.

## The Summary sheet

One row per module/sheet (Module | Area | Test Cases | Automated | Passed | Failed | Not Executed |
Blocked), plus a `TOTAL` row. Formulas:
```
Test Cases   = COUNTA('<Sheet>'!$A$7:$A$<end_row>)          -- non-CRUD sheets
             = COUNTA('<Sheet>'!$A$7:$A$<end_row>)-4         -- CRUD-banded sheets (subtract the 4 band rows)
Automated    = COUNTIF('<Sheet>'!$H$7:$H$<end_row>,"Yes")
Passed       = COUNTIF('<Sheet>'!$I$7:$I$<end_row>,"Passed")
Failed       = COUNTIF('<Sheet>'!$I$7:$I$<end_row>,"Failed")
Not Executed = COUNTIF('<Sheet>'!$I$7:$I$<end_row>,"Not Executed")
Blocked      = COUNTIF('<Sheet>'!$I$7:$I$<end_row>,"Blocked")
TOTAL row    = SUM(<col>5:<col><row above TOTAL>) for columns C-H
```
`<end_row>` is that sheet's true last content row — recompute it after every edit, don't trust
`ws.max_row` (openpyxl often reports stale higher values after row deletions/clears).

Adding a brand-new sheet means inserting a new Summary row via `ws.insert_rows()` — see the
critical pitfall below before doing this.

## Steps to build/update

1. **Determine scope**: which sheet(s), and whether this is a new sheet, appending rows to an
   existing sheet's bucket(s), or a workbook-wide sweep (e.g. a coverage audit). Check the current
   file state first (`wb.sheetnames`, row counts) — this workbook changes every session.
2. **Derive the full test surface** per [[derive-full-test-surface-from-objective]]: a
   field-validation objective almost always implies both Create *and* Edit coverage, not just the
   page it was first written against. When auditing, check EDIT rows mirror CREATE rows for every
   mandatory/format/boundary rule, and that VIEW rows confirm field presence/display for the
   fields central to the record.
3. **For large batches** (a new sheet from a raw checklist source, or a workbook-wide audit across
   20+ sheets): use background `Agent` calls or a `Workflow` pipeline — one agent per sheet/source
   file — rather than authoring hundreds of rows inline. Extract the relevant raw content to a
   per-sheet JSON file first so agents don't each re-read the whole workbook. Keep audits
   conservative: most sheets already have deep coverage, so only flag a gap the agent is confident
   is genuinely absent (a field with the same validation pattern established elsewhere on the
   *same* sheet, but missing for this field/bucket).
4. **Match existing style exactly** — copy `font`, `fill`, `border`, `alignment`, `number_format`
   from a template row in the same bucket (`copy.copy(...)`, not new `Font(...)` objects) onto
   every new/inserted row.
5. **Renumber, rebuild validations, update the nav caption and Summary row(s)** as described above.
6. **Validate on a scratch copy first** for any change touching more than ~5 rows or any Summary
   insertion — see Known pitfalls. Only apply to the live file once the dry run is clean.
7. **Verify after saving**: reload with openpyxl, confirm it opens with no errors, re-check IDs are
   sequential per sheet with no row holding a Scenario but a blank ID, confirm `ws.tables` is empty
   on every sheet, confirm no two merged ranges on any sheet overlap, and spot-check the Summary
   TOTAL/COUNTA ranges against the sheet's actual new end row.

## Known pitfalls (all caused real corruption/data-loss this session — check every time)

- **`ws.insert_rows()` does NOT shift merged-cell ranges below the insertion point.** This is the
  #1 corruption cause: a merge that should have moved down 1 row stays put, ends up overlapping a
  row it shouldn't, and Excel refuses to open the file cleanly ("we found a problem with some
  content..."). Never call `insert_rows` directly on a sheet that has merges (which is every sheet
  in this workbook, at minimum the header block A1:J1/A2:B3/C2:J3/A4:J4). Either (a) append at the
  end of a bucket instead of inserting mid-sheet wherever possible, or (b) write a wrapper that
  explicitly unmerges every range at/below the insertion point, calls `insert_rows`, then re-merges
  each shifted range one row down. After any `insert_rows` (including on the Summary sheet), always
  check for a stray merge sitting over the row you just inserted/the TOTAL row — unmerge and rewrite
  if found.
- **Stale Excel Table objects.** `wb.copy_worksheet()` (used when cloning a sheet's header/styling
  for a new sheet) can carry over a `ws.tables` entry whose `ref` range no longer matches the new
  sheet's actual content, and later row growth leaves *original* sheets' table refs stale too. A
  table `ref` cannot contain merged cells (which the CRUD bands introduce) and cannot point past
  actual content — either causes an Excel repair prompt. This workbook does not use/need Table
  functionality anywhere. Before saving any change, iterate every sheet and `del ws.tables[name]`
  for every entry found, regardless of whether you touched that sheet.
- **Don't key row-renumbering off column A.** When assigning fresh Test Case IDs to newly inserted
  rows, the loop must check column B (Scenario) for "does this row have content", not column A (ID)
  — column A is `None` on a just-inserted row by definition, so keying off it silently skips
  assigning an ID to every new row while still incrementing the band's displayed count. Verify after
  the fact: no row should have a non-empty Scenario and a missing/malformed ID.
- **File locking.** The live workbook is frequently open in Excel by the user. `openpyxl.load_workbook`
  raises `PermissionError` when locked — don't retry in a tight loop; ask the user to close it, or
  use a `Monitor`/background wait loop that polls every few seconds until it unlocks.
- **Python module-name shadowing.** Never name a scratch script `inspect.py` (or anything else that
  shadows a stdlib module openpyxl imports) in the same directory you run Python from — it silently
  breaks `import openpyxl` via a stale `__pycache__` entry with a confusing circular-import error.

## Notes
- Never author this as markdown — always `.xlsx` (see [[testcase-docs-excel-format]]).
- This is a different, more detailed format than [[qa-checklist-workbook]] (SL#/Test
  Objective/single free-text Status, no CRUD bands, no Summary formulas) — don't conflate the two;
  check which workbook/file the user means when ambiguous.
- When converting a raw source checklist (a `#/Area/Checklist item/Source/Status/Remarks`-style
  file) into this format, the source's terse "Verify that X" phrasing becomes this format's
  Scenario (cleaned up, typos fixed) + Expected Result (turned into a direct assertion) — don't
  just copy the raw text into one column.
