---
name: bug-report-writeup
description: >
  Format one or more already-found defects into the project's standard Jira bug-report block —
  red "Bug #N" title, bold Steps to reproduce (numbered), bold Observed behavior / Expected
  behavior (bulleted), and an Attachment with an embedded screenshot. Use whenever the user has
  findings from exploratory testing, a regression sweep, or manual review that need to be written
  up and/or posted as a Jira comment, as opposed to running a single ticket through a live test
  end-to-end (that full flow is [[jira-test-report]] instead).
---

# Bug report write-up format

Turns a defect you've already observed (from any source — live testing, a regression sweep, a
user-reported repro, log review) into the project's standard bug-report block, and optionally
posts it as a Jira comment. This is the **formatting/authoring** step; if you also need to drive
the live test yourself from a ticket, use the [[jira-test-report]] skill instead — it covers this
same output format as step 7 of a fuller workflow.

## Output format (Jira wiki markup, renders as in the reference screenshot)

For **each** bug:

```
h3. Bug #<N>: <one-sentence defect title, no trailing period, matches what's actually wrong>

*Steps to reproduce:*
# Login to the application.
# Navigate to <exact menu path, e.g. "the Lending Workbench lister">.
# <action>...
# <action that triggers the defect>.

*Observed behavior:*
* <what actually happened — one bullet per distinct symptom>.
* <a second symptom if there is one, e.g. "The column is not added to the lister view.">.

*Expected behavior:*
* <what should happen instead — one bullet per point, mirrors Observed's structure>.
* <second expected point if Observed had two>.

*Attachment:*
!<screenshot-filename>.png!
----
```

Formatting rules — match exactly, these are what "the standard format" means in this project:
- `h3. Bug #N: <title>` — no numbering gaps; number continues from whatever bugs already exist on
  the target ticket/comment (check the current highest `Bug #` first, don't restart at 1).
- `*Steps to reproduce:*` then a `# ` numbered list (space after `#`). Always start with
  "Login to the application." as step 1 unless the target doc has established a different
  first step.
- `*Observed behavior:*` and `*Expected behavior:*` are **bulleted** (`* `), not paragraphs — one
  bullet per distinct fact. A single-symptom bug still gets one bullet, not a bare sentence
  (compare the fuller multi-bullet screenshot reference against the older single-paragraph style
  in `Regression/Loan_Interest_Rate/_jira_comment.txt` — bulleted is the current standard; prefer
  it for new bugs).
- `*Attachment:*` on its own line, then `!filename.png!` on the next line (inline, no
  `|thumbnail` suffix needed unless the target document already uses thumbnails throughout —
  match whichever convention the destination comment already uses).
- Blank line before each `*...:*` label, or the preceding list swallows it.
- `----` separator after each bug's attachment line, before the next `h3.`.
- Bug title in the rendered view shows in **red** — this is Jira's default `h3.` + issue-link-style
  styling from the wiki renderer, not something to hand-format; don't add manual color markup.

## Screenshot requirement (non-negotiable)

Every bug must have a screenshot attached — see [[jira-bugs-need-screenshots]]. Never file or
write up a bug without one queued:
1. Capture a full-viewport screenshot the moment the defect is visible (error banner, wrong
   state, missing element).
2. Save under `Regression/<Module>/screenshots/<BUGID-or-slug>.png`, named
   `<MODULE>-<PAGE>-<slug>.png` (module/page codes in `Regression/README.md`).
3. Reference it in the `*Attachment:*` block with the exact filename.
4. If posting live to Jira, upload via the attachment panel/API **before** posting the comment
   body that references it, so the `!filename.png!` embed resolves.

## Steps

1. **Gather the findings**: for each bug, confirm you actually observed it (don't write up a
   suspected-but-unverified issue as if reproduced) — steps, observed behavior, and expected
   behavior per the app's actual documented/implied rule.
2. **Check the destination** for the next available Bug # (existing comment, existing doc) so
   numbering stays contiguous — see [[workbook-updated-every-run]] for the parallel rule on the
   regression workbook (add defects when found, mark unfiled ones provisional until posted).
3. **Capture and save the screenshot** per the requirement above, one per bug minimum.
4. **Write the block(s)** in the exact format above, one `h3.` section per bug, `----` between
   bugs.
5. **Post or save**:
   - Posting to Jira: switch the comment editor to Text (wiki-markup) mode, paste the body,
     attach screenshots first if not already uploaded, submit.
   - Not yet postable (no ticket access, ticket doesn't exist yet, batching for later): save the
     block(s) to `Regression/<Module>/_jira_comment.txt` (or append to the existing one) so the
     write-up isn't lost, and flag to the user that it's prepared but not filed.
6. **Update the tracking workbook** (Jira Bugs sheet / regression checklist) with the new
   defect(s) as soon as they're found, not only once filed — mark unfiled ones provisional/yellow
   per [[workbook-updated-every-run]].

## Notes
- One comment can hold many bugs — batch everything found in a session into a single post with
  multiple `h3.` blocks rather than one comment per bug, matching existing examples
  (`Regression/Loan_Interest_Rate/_jira_comment.txt` has 10 in one comment).
- Faithful reproduction over speed: only claim what was actually observed; a logical consequence
  of a proven constraint may be stated as such but not presented as a separately-run test.
- If a described defect can't be reproduced, don't force-fit a bug write-up — report that
  explicitly instead of fabricating steps/observed behavior.
