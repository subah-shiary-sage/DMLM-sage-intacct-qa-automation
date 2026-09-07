---
name: jira-test-report
description: >
  Given a Sage JIRA ticket key (e.g. IADSSL-1723), read the ticket description, execute the
  described manual test against the Sage Intacct app (release.intacct.com, Lending Management
  Entity by default), and report the result/defect as a comment on that ticket in the
  established IADSSL-1714 bug-report wiki-markup format, with a screenshot attached. Use whenever
  the user gives a JIRA number and asks to "do the task / test it and report in the comment", or
  references reporting a defect "in the predescribed format".
---

# JIRA test-and-report workflow

Turn a JIRA ticket into: (1) a live manual test in the Sage Intacct app, and (2) a defect/result
comment on the same ticket, formatted exactly like the bug reports on **IADSSL-1714**.

## Inputs
- **Ticket key** (required), e.g. `IADSSL-1723`. Ticket URL = `https://jira.sage.com/browse/<KEY>`.
  (Sage JIRA is self-hosted at **jira.sage.com** — NOT sage.atlassian.net.)
- Everything else (what to test, environment, credentials) comes from the ticket **Description**.

## Tools
- Browser automation: `playwright-mcp` tools (`browser_navigate`, `browser_snapshot`,
  `browser_click`, `browser_type`, `browser_take_screenshot`, `browser_file_upload`,
  `browser_tabs`, `browser_evaluate`). Load their schemas via ToolSearch first.
- The same Chrome profile is shared with JIRA (already logged in as the tester) — keep JIRA in
  tab 0 and drive the app in additional tabs.

## Steps

### 1. Read the ticket
Navigate to `https://jira.sage.com/browse/<KEY>` and read **Description** + **Environment detail**.
Extract: the acceptance criterion (what "correct" means), the env URL, company/user/password.
If a login redirect appears, wait a few seconds — SSO usually resolves the existing session.

### 2. Handle a locked browser profile (common)
If a playwright tool returns `Browser is already in use for ...mcp-chrome-<id>`, a stale Chrome is
holding the profile. **Do not kill it silently** — it may be another session. Ask the user first
(`AskUserQuestion`). On approval:
```bash
# find, kill, clear the singleton lock
Get-CimInstance Win32_Process -Filter "name='chrome.exe'" |
  Where-Object { $_.CommandLine -like '*mcp-chrome-<id>*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
# then remove <profile>\SingletonLock if present
```

### 3. Log in and reach the feature
Default env = **release.intacct.com**, entity = **Lending Management Entity (LME)**.
1. New tab → `https://release.intacct.com` → fill Company ID / User ID / Password from the ticket
   (e.g. `SNL_release_monthly` / `Admin` / `Aa123456!`) → Log in.
2. Click the entity switcher ("Top level") → **LME--Lending Management Entity**.
   ⚠️ The entity switch opens a **new tab** with a fresh session — `browser_tabs select` into it.
3. Open the module (e.g. **Lending Management**) → Setup menu → the feature's `+` (Create) or list.
   Menu item hrefs contain `config=snl.<object>.<action>` (e.g. `snl.loan-interest-rate.create`).

### 4. Execute the test
Reproduce the ticket's scenario faithfully and observe pass/fail. App gotchas
(see [[lme-master-data-seeding]] memory):
- Loan interest rate: Start date must be the **first day of a month**; ≥1 schedule row required;
  a **Revolving** loan type needs a row with Type=Interest.
- Interest rate field: backend regex `^(-?\d+)?(\.\d{1,2})?$` → **max 2 decimals** (this is the
  IADSSL-1723 defect: 4-decimal `5.1234` is rejected with HTTP 400).
- `xg-select` comboboxes only filter when typed character-by-character (`slowly:true`); grid-cell
  selects need a real ref click, not JS.
- Take a **full-viewport screenshot** the moment the result (error banner / saved record) is on
  screen.

### 5. Save the evidence screenshot
Copy it into the module's regression folder so it lives with the report:
`Regression/<Module>/screenshots/<BUGID>.png`
Naming: `<MODULE>-<PAGE>-<slug>.png`, e.g. `LIR-CREATE-rate-4decimals-rejected.png`
(module/page codes are in `Regression/README.md`). **Every defect must have a screenshot**
(see [[jira-bugs-need-screenshots]]).

### 6. Attach the screenshot to the ticket
On the JIRA tab: Attachments panel → "browse." → `browser_file_upload` with the absolute path.
Wait for "…has been attached successfully".

### 7. Post the comment in IADSSL-1714 format
Add comment → switch the editor to **Text** (wiki-markup) mode → paste the body below.
(For a classic full-page editor, go to `/secure/EditComment!default.jspa?id=<issueId>&commentId=<id>`
and set the `<textarea>` value.) Use blank lines between sections so lists render correctly.

**Template (Jira wiki markup) — matches IADSSL-1714:**
```
h2. Test environment

Login: [release.intacct.com|http://release.intacct.com/]

Credentials: SNL_release_monthly/{{{}Admin/Aa123456!{}}}
----
h2. <Module> – CRUD findings
h3. Bug #1 [<Page>]: <one-sentence defect title ending with a period>.

*Steps to reproduce:*
 # Log in to Sage Intacct at release.intacct.com.
 # Switch to the Lending Management Entity using the entity selector.
 # Navigate to <module> and open the <feature> list.
 # <action>...
 # Click Save.

*Observed behavior:*
 * <what actually happened, incl. exact error text / HTTP code>.

*Expected behavior:*
 * <what should happen per the ticket's acceptance criterion>.

*Attachment:*
!<BUGID>.png!
----
```
Format rules (do these exactly — they are what "the 1714 format" means):
- `h2.` for section headers, `h3. Bug #N [<Page>]:` for each defect, title ends with a period.
- Steps = ` # ` numbered list; Observed/Expected = ` * ` bullet list (note the leading space).
- **Blank line** before each `*...:*` block, else the list swallows it.
- Attachment reference is `!file.png!` — **no** `|thumbnail!` (renders inline full-size).
- `----` separators between the env block and each finding.
- If the test **passes**, still post: a short `h2. Test result` + `*Result:* PASS` note with the
  reproduction steps and a screenshot of the successful state.

### 8. Confirm
Verify the comment rendered (headings, lists, inline image). Report the comment id back to the
user. If reformatting a prior comment, **edit it** rather than adding a new one.

## Notes
- Faithful reproduction over speed: only claim what you actually observed. Logical consequences of
  a proven constraint (e.g. "regex allows max 2 dp ⇒ 5.12 would save") may be stated as such, not
  as separately-run tests.
- Don't leave stray records: if the save was rejected, nothing persisted — no cleanup needed. If a
  record WAS created for the test, delete it afterward.
- Reference example of a finished multi-bug comment: `Regression/Loan_Interest_Rate/_jira_comment.txt`.
