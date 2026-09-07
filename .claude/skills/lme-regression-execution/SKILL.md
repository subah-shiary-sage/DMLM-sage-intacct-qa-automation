---
name: lme-regression-execution
description: >
  Execute untested/failed scenarios from the LME regression workbook
  (Regression/LME_Regression_Consolidated.xlsx) against Sage Intacct, append any defects found to
  the running IADSSL-1714 bug list via the JIRA REST API (auto-numbered, Observed/Expected format,
  screenshot attached + embedded), write the results back into the workbook, and regenerate the
  HTML execution report. Use when asked to "test the untested scenarios / untested checklists",
  "update the checklist file", "report this bug in 1714", "add the missing attachments", or to
  retest a fix ticket (IADSSL-17xx) across LME listers.
---

# LME regression execution & 1714 bug reporting

Two jobs, usually together:
1. **Execute** checklist scenarios from the workbook against the app and record real results.
2. **Report** any defect into the **running bug list on IADSSL-1714** (not a new ticket), then
   update the workbook + HTML report.

> Sibling skill: `jira-test-report` handles *"test what a single ticket describes and comment on
> that ticket."* Use **this** skill for checklist execution and for appending to the #1714 list.

## Environment

| | |
|---|---|
| URL | `https://release.intacct.com` (resolves to **www-p303**) |
| Company / User / Password | `SNL_release_monthly` / `Admin` / `Aa123456!` |
| Company resolves to | `SNL_base_303_M` |
| Entity | **LME – Lending Management Entity** (switch after login) |
| Dev sandbox (fix retests) | `www-p308.intacct.com/users/<dev>/projects.ia-app/` + `sandboxCollection` cookie set **after** login |

## Credentials — do not hardcode

The JIRA bearer token is **not** stored in this file. Reuse it from an existing script in the
session scratchpad (`add_bug_*.py`, `comment_*.py`) or ask the user. Never commit it into the repo.

---

## Part 1 — Execute checklist scenarios

### Find the untested items
Status values are constrained to four: **Passed / Failed / Untested / To be tested**
(each execution sheet has a dropdown on its status column).

| Sheet | Status col | First data row |
|---|---|---|
| Loan Account / Type / Category / Fee Type / Adjustment – CRUD | 6 | 7 |
| Loan Interest Rate – CRUD | 6 | 2 |
| Loan Account / Config / Edit-View-Delete / Loan Statements / Lending Workbench listers | 3 | 6 |

```python
# rows still open on a sheet
[r for r in range(first, ws.max_row+1)
   if str(ws.cell(r,col).value).strip() in ('Untested','To be tested')]
```

### Classify before testing
Split the open items into:
- **UI-executable** — do these.
- **Blocked-by-design** — root-vs-child multi-entity, closed-period / statements-already-generated,
  and `SNLLOAN*` database checks. Leave as `To be tested` **with a note saying why**. Do not mark
  these Passed.

Say the split out loud to the user before a long run so expectations are set.

### Record honestly
- Only mark `Passed`/`Failed` for what you actually observed.
- Feature genuinely absent on that page → `Untested` + note `N/A - <reason>`.
- Couldn't confirm because the page misbehaved → `To be tested` + note what to re-check manually.
  **Do not** file a bug off an unconfirmed automation artifact.

---

## Part 2 — Report a defect into IADSSL-1714

All LME defects append to **one comment**: issue `IADSSL-1714`, comment id **`4855245`**.
It is **append-only** — GET the body, append, PUT the whole thing back.

### Auto-number the bug
```python
cur  = GET /rest/api/2/issue/IADSSL-1714/comment/4855245 -> ['body']
nums = [int(n) for n in re.findall(r'Bug #(\d+)', cur)]
nextn = max(nums)+1
new_body = cur.rstrip('\r\n') + '\r\n' + block      # NL = '\r\n' throughout
```

### Bug block format (current house style)
```
----
h3. Bug #<N> [Lending Management > <Page> > <Action>]: <one-sentence plain-language title>.

*Steps to reproduce:*
 # Log in and switch to the Lending Management Entity.
 # <step>
 # Click *Save*.

*Observed behavior:*
 * <what actually happens, in plain language>

*Expected behavior:*
 * <what should happen>

*Screenshot:*
!bug<N>-<slug>.png!
```

Rules that define "the format":
- Headings are **`*Observed behavior:*` / `*Expected behavior:*`** — never "What happens".
- **Plain, human language.** No stack traces or internal object names in the title; quote exact
  error strings inside `{{...}}` in the Observed bullets only where they are the evidence.
- **No "Notes / evidence" section** — the user removed these; keep blocks to
  Steps / Observed / Expected / Screenshot.
- ` # ` numbered steps, ` * ` bullets (leading space matters), blank line before each `*...:*`.
- `----` separator before each new bug.
- Every bug gets a screenshot: `!file.png!` (no `|thumbnail`).

### Screenshot — capture, upload, embed
**Only screenshots you capture yourself can be attached.** Images the user pastes into chat are
never written to disk and cannot be uploaded — if you have no file, either capture it in-app or
ask the user to save the PNG into `.playwright-mcp\`.

```python
# 1. capture in-app  -> lands in .playwright-mcp\<name>.png
# 2. upload
POST /rest/api/2/issue/IADSSL-1714/attachments
     headers: X-Atlassian-Token: no-check, multipart/form-data
# 3. embed !<name>.png! inside that bug's block, then PUT the comment
```
Make the embed step **idempotent** — skip a bug whose block already contains `!<file>!`, otherwise
re-runs create duplicate attachments.

### Mirror into the workbook
Add a row to sheet **`Jira Bugs (IADSSL-1714)`** (cols: Bug # / Module / Summary / Status / Related
checklist) and bump the `#1-#NN` / `NN defects` counters in the **Summary** notes rows.

---

## Part 3 — Update workbook + report

After each batch:
1. Write `status` + a dated evidence note prefixed
   `EXECUTED <YYYY-MM-DD> (release www-p303, SNL_base_303_M, LME entity): ...`
2. Colour the status cell: Passed `C6EFCE`, Failed `FFC7CE`, Untested `D9D9D9`, To be tested `FFEB9C`.
3. Recompute the **Summary** coverage table (rows 9–19, TOTAL on row 20) by re-counting each sheet.
4. Regenerate `Regression/LME_Untested_Execution_Report.html` — standalone HTML, summary cards,
   per-scenario table, a **Defects/gaps** list, an **N/A** list, and a **Remaining work** section.
   Keep light+dark CSS (`prefers-color-scheme`).

---

## App gotchas (learned the hard way)

- **Entity switch opens a NEW TAB** with a fresh session — `browser_tabs select` into it and close
  the stale one, or later clicks silently target the dead session.
- **Pendo guide overlay** blocks clicks after login:
  `document.querySelectorAll('[id^="pendo-"],._pendo-backdrop').forEach(e=>e.remove())`.
  A `.nav-popup-overlay` from an open menu blocks grid clicks the same way.
- **"Lists beta" HTTP 500** (`api-p303`) takes down *every* LME lister **and** create form on
  p303 for hours at a time. Symptom: *"We're having trouble turning on the Lists beta interface."*
  It is environmental — don't chase it as a bug; re-check later, and say so plainly.
- **React-controlled inputs ignore programmatic `value` setting.** Native setter + `input` event
  works for plain fields but **not** for schedule/adjustment grid cells — those need real
  `browser_type` / `browser_click` on a ref.
- **Grid links are `<button role="link">`, not `<a>`** — `querySelector('a')` finds nothing. Walk
  up from the text leaf to the nearest `A|BUTTON|[role=link]` ancestor.
- Lister nav: menu hrefs carry `config=snl.<object>.<action>` plus a per-session `eSecReq` token.
  Re-open the module menu to get fresh links rather than reusing an old URL.
- Sandbox cookie for dev-build retests must be set **after** login (before login breaks auth).
- **Snapshots are huge.** Batch many assertions into one `browser_evaluate` returning a small
  object; don't call `browser_snapshot` on a loaded grid unless you need it.

## Known-defect signatures worth recognising
- Untranslated keys leaking to UI: `IA.MESSAGE_ERROR_LABEL`, `IA.COLLAPSE`, `IA.ATTACHMENT`,
  `IA.TOGGLE_BUTTON_LABEL`, `IA.NO_RESULTS_FOUND`.
- Raw Java NPE + `Cannot read properties of undefined (reading 'placeholders')` on save = the
  Bug #54 family (fixed for Adjustment, still open on Interest Rate → Bug #85).
- Validation naming the internal field instead of the on-screen label ("Loan type" vs "Type") =
  Bug #75 family.
- Adjustment edit-page "Adjustment details" balances blank / double-counted = Bugs #82–#84.

## Ground rules
- Report outcomes faithfully: if a batch covered 15 of 292, say so — never imply full coverage.
- Don't leave test data behind: a rejected save persists nothing; if a record *was* created, delete
  it. Cancel out of edit forms rather than saving.
- Prefer several small verified batches over one large unverified sweep.
