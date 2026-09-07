---
name: qa-checklist-workbook
description: >
  Generate or update a Sage Intacct QA test-checklist workbook (.xlsx) in the project's standard
  format: a header block (Prepared By / Executed By / Updated On / Common steps + a live status
  count summary), followed by a numbered Test Objective list grouped under bold section bands
  (e.g. "Journal entry", "CREATE"), with dropdown-validated Status column(s) color-coded
  Passed/Failed/Untested/To be tested. Use whenever the user asks to "prepare a checklist",
  "build a test case sheet", or references the Prepared By/Total Test Cases layout — always as
  .xlsx, never markdown (see [[testcase-docs-excel-format]]).
---

# QA checklist workbook format

Reproduces the exact layout already used across this project's checklists (e.g.
`regression checklist.xlsx`, sheet "Loan Account - CRUD", and
`Test_Cases_and_Checklists/CHECKLIST_Depository_Management_Regression.xlsx`). Build with
**openpyxl**. One sheet per module/object unless the user says otherwise; multiple modules go in
one workbook as separate sheets, matching the existing consolidated checklists.

## Layout (row-by-row, 1-indexed)

**Row 1** — `A1` "Prepared By" (bold) | `B1:C1` merged, the name | `D1` "Total Test Cases" (bold) | `E1` count
**Row 2** — `A2` "Executed By" (bold) | `B2:C2` name | `D2` "Passed" (bold) | `E2` count
**Row 3** — `A3` "Updated On" (bold) | `B3:C3` date (`YYYY-MM-DD`) | `D3` "Failed" (bold) | `E3` count
**Row 4** — `A4:A5` merged "Common steps" (bold) | `B4` step 1 (e.g. "1. Login to Sage Intacct") | `D4` "Untested" (bold) | `E4` count
**Row 5** — `B5` step 2 (e.g. "2. Go to Application-> <Module>") | `D5` "To be tested" (bold) | `E5` count
**Row 6** — column headers (bold, white text on dark-blue fill `1F4E79`): `A6` "SL#", `B6:E6` merged "Test Objective", `F6` "Test Status", `G6` "Test Status" (a second, duplicate status column — this project runs two independent status trackers side by side; if the user only asked for one, use a single `F6` "Test Status" + `G6` "Comment" instead — ask if unclear from context)
**Row 7+** — one row per test case, OR a full-width section band row.

### Section band rows
A bold row spanning `A:G` (or `B:E` if keeping SL#/status columns visible), light-blue fill
(`D6E4F0`), holding just the section name (e.g. "Journal entry", "CREATE", "EDIT", "DELETE",
"LISTER"). Insert one before each logical group of test objectives. Do not number these rows in
the SL# column.

### Test case rows
- `A` — sequential integer SL# (restart or continue numbering per the user's existing convention —
  check the target sheet/workbook first; most checklists number continuously through the whole
  sheet, not restarting per section).
- `B:E` merged — the Test Objective text, phrased as "Verify that <behavior>" or "Verify <thing>
  is present/functional" (see [[derive-full-test-surface-from-objective]] for how to derive the
  full Create+Edit test surface from a validation objective, not just what's explicitly stated).
- `F` (and `G` if duplicated) — Status cell, restricted to a dropdown list `Passed,Failed,Untested,To be tested`
  via `DataValidation(type="list", formula1='"Passed,Failed,Untested,To be tested"')` applied to
  the full status column range (e.g. `F7:F<lastrow>`). Default value on creation: `Untested`.
- `G` (if used as Comment, not a duplicate status column) — free text, notes/evidence summary.

## Color coding

| Status / label | Fill hex | Font color |
|---|---|---|
| Passed | `C6EFCE` | `006100` |
| Failed | `FFC7CE` | `9C0006` |
| Untested | `FFEB9C` (tan/yellow) | `9C6500` |
| To be tested | `D9D9D9` (gray) | `000000` |
| Header row (row 6) | `1F4E79` (dark blue) | `FFFFFF`, bold |
| Section band row | `D6E4F0` (light blue) | inherit, bold |
| Row 1-5 header block | `F2F6FB` (very light blue) | inherit |

Apply the Passed/Failed/Untested/"To be tested" fill to **both** the summary count cells (E2:E5,
matching each label in D2:D5) and every Status cell in the table that holds that value — this is
what makes the dropdown look like colored pills in the screenshot reference. Recompute E2:E5 as
formulas (`=COUNTIF(F7:F<lastrow>,"Passed")` etc.) rather than static numbers, so counts stay
correct if the user edits statuses later — unless the workbook already uses static numbers
elsewhere in the project, in which case match that convention instead.

## Column widths (match existing checklists)
`A`=12, `B`=30, `C`=18, `D`=14, `E`=10, `F`=14, `G`=14 (or 58 if `G` is a free-text Comment column).

## Formatting details
- Freeze panes at the first data row (e.g. `A7`) so the header block and column headers stay
  visible while scrolling.
- Thin borders under the row-6 header and around every data cell (matches existing sheets).
- Row 6 header height slightly taller if wrapping "Test Objective"-style long labels.
- Wrap text on the merged Test Objective cells when the objective text is long (multi-line
  objectives are common, e.g. listing all fields in a section).

## Steps to build

1. **Determine scope**: which module(s)/object(s), and whether this is a new workbook or a new
   sheet/update to an existing one. Prefer updating an existing workbook (see
   [[workbook-updated-every-run]]) over creating a parallel file.
2. **Derive the full test objective list** per [[derive-full-test-surface-from-objective]] —
   don't just list what's explicitly requested; work out Create + Edit (and Delete/Lister where
   applicable) coverage from the module's actual fields and behavior.
3. **Group into sections** that match the real UI flow (e.g. page sections, CRUD phases, or
   functional areas like "Journal entry", "Config Listers").
4. Build with openpyxl: header block → column headers → section bands + numbered rows, applying
   the fills/borders/dropdown above.
5. Set `Prepared By` / `Executed By` to the user's name if known from context, `Updated On` to
   today's date, `Common steps` to the actual login + navigation path for that module.
6. Save as `.xlsx` into `Test_Cases_and_Checklists/` (or the existing workbook's location), named
   `TEST_CASES_<Module>.xlsx` or `CHECKLIST_<Scope>_Regression.xlsx` matching existing naming.
7. Re-open and spot check: merged ranges intact, dropdown validation present, colors applied,
   counts correct.

## Notes
- Never author this as markdown — always `.xlsx` (see [[testcase-docs-excel-format]]).
- If updating counts/status on an existing sheet after live execution, don't hand-type "Passed" —
  set the cell value AND re-apply the corresponding fill/font color pair from the table above, or
  the cell will show correct text on a stale color.
- If the workbook mixes a duplicate status column (F and G both "Test Status") vs. a Comment
  column, check the target file's existing header row first — don't assume; both conventions
  exist in this project's files.
