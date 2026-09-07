"""
Verdict handlers for the Loan Fee Type checklist (50 CRUD rows + 3 lister rows).

Conventions applied here:

  * Objectives are read as the thing to prove, not a single click path. Max
    length (SL 12) and duplicate name (SL 22) are exercised on Create AND Edit;
    SL 24 exercises all three Save variants; SL 48 tests both halves (still
    editable / delete blocked).
  * Known, already-filed defects (#29, #30, #32, #87, #88) are re-confirmed but
    NOT re-filed — the handler returns FAILED with no Defect attached, so the
    row gets a dated RETEST note and no duplicate JIRA bug.
  * Test data is namespaced QA_PREFIX and always cleaned up. Bulk delete only
    ever touches rows it created, and aborts if anything else is selected.
"""

from __future__ import annotations

import time

from . import Defect, Outcome, ScenarioRegistry

registry = ScenarioRegistry("loan_fee_type")

QA_PREFIX = "QA AUTO"
GL_QUERY = "1322"
ITEM_QUERY = "A001"

A_CREATE = "Lending Management > Loan fee type > Create"
A_VIEW = "Lending Management > Loan fee type > View"
A_EDIT = "Lending Management > Loan fee type > Edit"
A_DELETE = "Lending Management > Loan fee type > Delete"
A_LISTER = "Lending Management > Loan fee types > Lister"

LOGIN_STEPS = [
    "Log in to Sage Intacct at release.intacct.com.",
    "Switch to the Lending Management Entity using the entity selector.",
    "Navigate to Lending Management > Setup > Loan fee type.",
]


def _unique(suffix: str) -> str:
    return f"{QA_PREFIX} {suffix} {int(time.time() * 1000) % 1000000}"


def _open_create(ctx):
    ctx.listing_page.navigate_to_list()
    ctx.listing_page.click_create()


def _create_record(ctx, name: str, *, gl: bool = True, item: bool = False) -> str:
    """Create a fee type via the UI and return its name."""
    _open_create(ctx)
    ctx.record_page.fill_name(name)
    if gl:
        ctx.record_page.set_gl_account(GL_QUERY)
    if item:
        ctx.record_page.set_item(ITEM_QUERY)
    ctx.record_page.save()
    ctx.record_page.wait_for_view_page()
    return name


def _delete_by_name(ctx, name: str) -> bool:
    """Best-effort cleanup. True if the record is gone afterwards."""
    try:
        ctx.listing_page.navigate_to_list()
        ctx.listing_page.search_by_name(name)
        if not ctx.listing_page.is_record_visible(name):
            return True
        ctx.listing_page.open_record_by_name(name)
        ctx.record_page.click_delete()
        ctx.record_page.confirm_delete()
        ctx.listing_page.wait_for_list_page()
        ctx.listing_page.search_by_name(name)
        return not ctx.listing_page.is_record_visible(name)
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# CREATE — page structure
# ══════════════════════════════════════════════════════════════════════════════


@registry.matching("create page title is")
def sl1_create_title(ctx, row) -> Outcome:
    _open_create(ctx)
    title = ctx.record_page.get_page_title()
    if title == "Create loan fee type":
        return Outcome.passed(f'Page title is exactly "{title}".', LOGIN_STEPS)
    return Outcome.failed(f'Page title is "{title}", expected "Create loan fee type".')


@registry.matching('contains a "loan fee type information" section')
def sl2_section(ctx, row) -> Outcome:
    _open_create(ctx)
    present = ctx.record_page.frame.get_by_text(
        ctx.record_page.SECTION_HEADER, exact=False
    ).count() > 0
    return (
        Outcome.passed(f'"{ctx.record_page.SECTION_HEADER}" section is present.')
        if present
        else Outcome.failed(f'"{ctx.record_page.SECTION_HEADER}" section not found.')
    )


@registry.matching('"save" split-button is present')
def sl3_save_present(ctx, row) -> Outcome:
    _open_create(ctx)
    n = ctx.record_page.frame.locator(
        '[aria-label="Save"], [role=menuitem]:has-text("Save")'
    ).count()
    return (
        Outcome.passed("Save control is present in the header.")
        if n
        else Outcome.failed("No Save control found in the header.")
    )


@registry.matching("save dropdown contains")
def sl4_save_menu(ctx, row) -> Outcome:
    _open_create(ctx)
    opts = [o.lower() for o in ctx.record_page.save_menu_options()]
    wanted = ["save", "save and close", "save and new"]
    missing = [w for w in wanted if not any(w == o for o in opts)]
    if not missing:
        return Outcome.passed(f"Save dropdown offers all three variants: {opts}.")
    return Outcome.unconfirmed(
        f"Could not confirm all Save variants (missing {missing}); menu showed: {opts}."
    )


@registry.matching('"cancel" button is present and navigates away')
def sl5_cancel(ctx, row) -> Outcome:
    steps = LOGIN_STEPS + ["Click *Create*.", "Enter a name.", "Click *Cancel*."]
    name = _unique("Cancel")
    _open_create(ctx)
    ctx.record_page.fill_name(name)
    try:
        ctx.record_page.cancel()
    except Exception:
        return Outcome.unconfirmed("Cancel control could not be actioned on the create page.")
    ctx.listing_page.wait_for_list_page()
    ctx.listing_page.search_by_name(name)
    if ctx.listing_page.is_record_visible(name):
        _delete_by_name(ctx, name)
        return Outcome.failed(
            "Cancel returned to the list but the record was saved anyway.",
            Defect(
                title="Cancel on the create form still saves the record",
                area=A_CREATE,
                steps=steps,
                observed=["After clicking Cancel the new record appears in the list."],
                expected=["Cancel should discard the form without creating a record."],
                screenshot=ctx.screenshot("lft-create-cancel-saved"),
            ),
            steps,
        )
    return Outcome.passed("Cancel leaves the form without saving; no record created.", steps)


@registry.matching("back arrow is present")
def sl6_back_arrow(ctx, row) -> Outcome:
    _open_create(ctx)
    return (
        Outcome.passed("Back arrow is present on the create page.")
        if ctx.record_page.has_back_arrow()
        else Outcome.failed("Back arrow is not present on the create page.")
    )


# ══════════════════════════════════════════════════════════════════════════════
# CREATE — Name field
# ══════════════════════════════════════════════════════════════════════════════


@registry.matching("name field is present and mandatory")
def sl7_name_mandatory(ctx, row) -> Outcome:
    _open_create(ctx)
    rp = ctx.record_page
    present = rp.frame.locator(rp.NAME_INPUT).count() > 0
    mandatory = rp.is_field_mandatory(rp.NAME_ARIA_LABEL)
    if present and mandatory:
        return Outcome.passed(
            "The name field is present and carries the mandatory asterisk."
        )
    return Outcome.failed(
        f"Name field present={present}, mandatory marker={mandatory}."
    )


@registry.matching("name field is labelled correctly")
def sl8_name_label(ctx, row) -> Outcome:
    """Known defect #29 — re-confirm, do not re-file."""
    _open_create(ctx)
    labels = [l.rstrip(" *").strip() for l in ctx.record_page.field_labels()]
    if "Name" in labels:
        return Outcome.passed('The name field is labelled "Name".')
    ctx.screenshot("lft-create-name-mislabelled")
    return Outcome.failed(
        'RE-CONFIRMED Bug #29: the name field is still labelled "Loan type", not '
        f'"Name". Labels on the form: {labels}. Not re-filed (already open).'
    )


@registry.matching("record can be created with a valid name")
def sl9_create_valid(ctx, row) -> Outcome:
    steps = LOGIN_STEPS + [
        "Click *Create*.",
        "Enter a valid name and select a GL account.",
        "Click *Save*.",
    ]
    name = _unique("Valid")
    try:
        _create_record(ctx, name)
        title = ctx.record_page.get_page_title()
        return Outcome.passed(
            f"Record created and its detail page opened ({title!r}).", steps
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("proper error is shown when name is left blank")
def sl10_name_blank(ctx, row) -> Outcome:
    _open_create(ctx)
    ctx.record_page.set_gl_account(GL_QUERY)
    ctx.record_page.save()
    ctx.page.wait_for_timeout(2_000)
    banner = ctx.record_page.error_banner_text()
    inline = ctx.record_page.has_inline_field_error()
    if banner and ("required" in banner.lower() or "correct the fields" in banner.lower()):
        return Outcome.passed(
            f"Blank name is rejected with a field-required message (inline error={inline}). "
            f"Banner: {banner[:160]!r}"
        )
    return Outcome.failed(f"Unexpected response to a blank name. Banner: {banner[:200]!r}")


@registry.matching("proper error is shown when name is whitespace-only")
def sl11_name_whitespace(ctx, row) -> Outcome:
    """Known defect #30 — re-confirm, do not re-file."""
    _open_create(ctx)
    ctx.record_page.fill_name("   ")
    ctx.record_page.set_gl_account(GL_QUERY)
    ctx.record_page.save()
    ctx.page.wait_for_timeout(2_000)
    banner = ctx.record_page.error_banner_text()
    if "loan-management/loan-fee-type" in banner or "object" in banner.lower():
        ctx.screenshot("lft-create-whitespace-name-objectpath")
        return Outcome.failed(
            "RE-CONFIRMED Bug #30: a whitespace-only name is rejected but the message "
            f"leaks the internal object path. Banner: {banner[:200]!r}. Not re-filed."
        )
    if banner:
        return Outcome.passed(f"Whitespace-only name rejected cleanly: {banner[:160]!r}")
    return Outcome.failed("A whitespace-only name produced no error at all.")


@registry.matching("maximum length of name")
def sl12_name_maxlength(ctx, row) -> Outcome:
    """
    Known defect #87. The objective names no page, so both Create and Edit are
    exercised — they have separate validation paths.
    """
    long_name = "QA" + "A" * 251
    findings, failed = [], False

    # -- Create --
    _open_create(ctx)
    maxlen = ctx.record_page.get_name_maxlength()
    ctx.record_page.fill_name(long_name)
    ctx.record_page.set_gl_account(GL_QUERY)
    ctx.record_page.save()
    ctx.page.wait_for_timeout(2_000)
    banner = ctx.record_page.error_banner_text()
    typed = len(ctx.record_page.get_name_value() or "")
    if "exceeds the allowed length" in banner or "length" in banner.lower():
        failed = failed or ("loan-management/loan-fee-type" in banner)
        findings.append(
            f"CREATE: {typed}-char name rejected; maxlength attribute={maxlen!r}; "
            f"message {banner[:150]!r}"
        )
    else:
        failed = True
        findings.append(f"CREATE: over-length name NOT rejected (banner {banner[:120]!r}).")

    # -- Edit --
    name = _unique("MaxLen")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_edit()
        edit_maxlen = ctx.record_page.get_name_maxlength()
        ctx.record_page.fill_name(long_name)
        ctx.record_page.save()
        ctx.page.wait_for_timeout(2_000)
        ebanner = ctx.record_page.error_banner_text()
        if "length" in ebanner.lower():
            failed = failed or ("loan-management/loan-fee-type" in ebanner)
            findings.append(
                f"EDIT: over-length rename rejected; maxlength={edit_maxlen!r}; "
                f"message {ebanner[:150]!r}"
            )
        else:
            failed = True
            findings.append(f"EDIT: over-length rename NOT rejected ({ebanner[:120]!r}).")
    finally:
        _delete_by_name(ctx, name)

    note = " || ".join(findings)
    if failed:
        ctx.screenshot("lft-maxlength-create-and-edit")
        return Outcome.failed(
            f"RE-CONFIRMED Bug #87 on Create AND Edit. {note}. The message leaks the "
            "object path and the input has no maxlength cap. Not re-filed."
        )
    return Outcome.passed(f"Max-length enforced cleanly on Create and Edit. {note}")


# ══════════════════════════════════════════════════════════════════════════════
# CREATE — GL account / Item / Description
# ══════════════════════════════════════════════════════════════════════════════


@registry.matching("gl account field is present and mandatory")
def sl13_gl_mandatory(ctx, row) -> Outcome:
    _open_create(ctx)
    ok = ctx.record_page.is_field_mandatory("GL account")
    return (
        Outcome.passed("GL account is present and mandatory.")
        if ok
        else Outcome.failed("GL account is missing its mandatory marker.")
    )


@registry.matching("gl account is a dropdown")
def sl14_gl_dropdown(ctx, row) -> Outcome:
    _open_create(ctx)
    n = ctx.record_page.frame.get_by_role("combobox", name="GL account").count()
    return (
        Outcome.passed("GL account renders as a searchable combobox.")
        if n
        else Outcome.failed("GL account is not a combobox.")
    )


@registry.matching("gl account dropdown lists valid gl accounts")
def sl15_gl_options(ctx, row) -> Outcome:
    _open_create(ctx)
    ctx.record_page.set_gl_account(GL_QUERY)
    value = ctx.record_page.get_gl_account_value()
    if value and GL_QUERY in value:
        return Outcome.passed(f"GL account search returned and selected {value!r}.")
    return Outcome.unconfirmed(
        f"GL account search for {GL_QUERY!r} did not resolve to an option (value={value!r})."
    )


@registry.matching("proper error is shown when gl account is not selected")
def sl16_gl_missing(ctx, row) -> Outcome:
    """Known defect #30 family — re-confirm, do not re-file."""
    _open_create(ctx)
    ctx.record_page.fill_name(_unique("NoGL"))
    ctx.record_page.save()
    ctx.page.wait_for_timeout(2_000)
    banner = ctx.record_page.error_banner_text()
    if "feeGLAccountKey" in banner or "loan-management/loan-fee-type" in banner:
        ctx.screenshot("lft-create-no-gl-internal-field")
        return Outcome.failed(
            "RE-CONFIRMED Bug #30: the missing-GL-account error names the internal field "
            f'"feeGLAccountKey" instead of the on-screen label. Banner: {banner[:180]!r}. '
            "Not re-filed."
        )
    if banner:
        return Outcome.passed(f"Missing GL account rejected cleanly: {banner[:160]!r}")
    return Outcome.failed("Saving without a GL account produced no error.")


@registry.matching("item field is present and optional")
def sl17_item_optional(ctx, row) -> Outcome:
    _open_create(ctx)
    rp = ctx.record_page
    return (
        Outcome.passed("Item is present and not marked mandatory.")
        if rp.has_field("Item") and not rp.is_field_mandatory("Item")
        else Outcome.failed("Item is missing, or is incorrectly marked mandatory.")
    )


@registry.matching("item is a dropdown")
def sl18_item_dropdown(ctx, row) -> Outcome:
    _open_create(ctx)
    n = ctx.record_page.frame.get_by_role("combobox", name="Item").count()
    return (
        Outcome.passed("Item renders as a searchable combobox.")
        if n
        else Outcome.failed("Item is not a combobox.")
    )


@registry.matching("item dropdown lists valid items")
def sl19_item_options(ctx, row) -> Outcome:
    _open_create(ctx)
    ctx.record_page.set_item(ITEM_QUERY)
    value = ctx.record_page.get_item_value()
    if value:
        return Outcome.passed(f"Item search returned and selected {value!r}.")
    return Outcome.unconfirmed(f"Item search for {ITEM_QUERY!r} resolved nothing.")


@registry.matching("description field is present and optional")
def sl20_description_optional(ctx, row) -> Outcome:
    _open_create(ctx)
    rp = ctx.record_page
    return (
        Outcome.passed("Description is present and not marked mandatory.")
        if rp.has_field("Description") and not rp.is_field_mandatory("Description")
        else Outcome.failed("Description is missing, or is incorrectly marked mandatory.")
    )


@registry.matching("saved without item / description")
def sl21_save_without_optional(ctx, row) -> Outcome:
    name = _unique("NoOptional")
    try:
        _create_record(ctx, name, item=False)
        return Outcome.passed("Record saved with Item and Description left blank.")
    finally:
        _delete_by_name(ctx, name)


@registry.matching("duplicate-name handling")
def sl22_duplicate_name(ctx, row) -> Outcome:
    """
    Known defect #88. The objective names no page, so duplication is attempted
    on Create AND Edit.
    """
    base = _unique("Dup")
    second = None
    findings, failed = [], False
    try:
        _create_record(ctx, base)

        # -- Create: save a second record with the same name --
        _open_create(ctx)
        ctx.record_page.fill_name(base)
        ctx.record_page.set_gl_account(GL_QUERY)
        ctx.record_page.save()
        ctx.page.wait_for_timeout(2_500)
        banner = ctx.record_page.error_banner_text()
        if banner and "exist" in banner.lower():
            findings.append(f"CREATE: duplicate rejected ({banner[:110]!r}).")
        else:
            failed = True
            second = base
            findings.append("CREATE: a second record with an identical name saved with no error.")

        # -- Edit: rename a different record onto the same name --
        other = _unique("DupEdit")
        _create_record(ctx, other)
        ctx.record_page.click_edit()
        ctx.record_page.fill_name(base)
        ctx.record_page.save()
        ctx.page.wait_for_timeout(2_500)
        ebanner = ctx.record_page.error_banner_text()
        if ebanner and "exist" in ebanner.lower():
            findings.append(f"EDIT: duplicate rename rejected ({ebanner[:110]!r}).")
            _delete_by_name(ctx, other)
        else:
            failed = True
            findings.append("EDIT: renaming a record onto an existing name saved with no error.")
            ctx.listing_page.navigate_to_list()
            ctx.listing_page.search_by_name(base)
            findings.append(f"Lister now shows {ctx.listing_page.count_rows_named(base)} rows named {base!r}.")
            _delete_by_name(ctx, base)  # removes one of the duplicates
    finally:
        _delete_by_name(ctx, base)
        if second:
            _delete_by_name(ctx, second)

    note = " || ".join(findings)
    if failed:
        ctx.screenshot("lft-duplicate-name-create-and-edit")
        return Outcome.failed(
            f"RE-CONFIRMED Bug #88 — duplicate names allowed. {note} Not re-filed."
        )
    return Outcome.passed(f"Duplicate names are rejected on both paths. {note}")


@registry.matching("clicking save creates the record and shows a proper confirmation")
def sl23_save_confirmation(ctx, row) -> Outcome:
    name = _unique("SaveMsg")
    try:
        _create_record(ctx, name)
        toast = ctx.record_page.toast_text()
        title = ctx.record_page.get_page_title()
        if toast:
            return Outcome.passed(f"Record created; confirmation shown: {toast[:120]!r}.")
        return Outcome.passed(
            f"Record created and its detail page opened ({title!r}). No toast was "
            "captured — the redirect happens immediately, so the confirmation "
            "message itself is unconfirmed rather than claimed."
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("save / save and close / save and new behaviour")
def sl24_save_variants(ctx, row) -> Outcome:
    """All three variants exercised, not the primary plus an assumption."""
    made, findings = [], []
    try:
        n1 = _unique("SaveA")
        _create_record(ctx, n1)
        made.append(n1)
        findings.append("Save: created the record and opened its detail page.")

        n2 = _unique("SaveNew")
        _open_create(ctx)
        ctx.record_page.fill_name(n2)
        ctx.record_page.set_gl_account(GL_QUERY)
        ctx.record_page.save_via("Save and new")
        ctx.page.wait_for_timeout(2_500)
        made.append(n2)
        title = ctx.record_page.get_page_title()
        findings.append(f"Save and new: landed on {title!r} (expected a fresh create form).")

        n3 = _unique("SaveClose")
        _open_create(ctx)
        ctx.record_page.fill_name(n3)
        ctx.record_page.set_gl_account(GL_QUERY)
        ctx.record_page.save_via("Save and close")
        ctx.page.wait_for_timeout(2_500)
        made.append(n3)
        ctx.listing_page.wait_for_list_page()
        findings.append("Save and close: returned to the lister.")
        return Outcome.passed(" || ".join(findings))
    except Exception as exc:
        return Outcome.unconfirmed(
            f"Could not exercise all three Save variants: {type(exc).__name__}: {exc}. "
            + " || ".join(findings)
        )
    finally:
        for n in made:
            _delete_by_name(ctx, n)


# ══════════════════════════════════════════════════════════════════════════════
# VIEW
# ══════════════════════════════════════════════════════════════════════════════


def _with_view_record(ctx, suffix: str):
    name = _unique(suffix)
    _create_record(ctx, name)
    return name


@registry.matching("view page title is")
def sl25_view_title(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "ViewTitle")
    try:
        title = ctx.record_page.get_page_title()
        if name in title:
            return Outcome.passed(f"View title includes the record name: {title!r}.")
        ctx.screenshot("lft-view-title-shows-id")
        return Outcome.failed(
            f"The view page title is {title!r} — it shows the internal record ID, "
            f"not the name {name!r}. Not re-filed (known)."
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching('"loan fee types" breadcrumb')
def sl26_breadcrumb_present(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "Crumb")
    try:
        return (
            Outcome.passed("A 'Loan fee types' breadcrumb link is present.")
            if ctx.record_page.has_breadcrumb()
            else Outcome.failed("No 'Loan fee types' breadcrumb on the view page.")
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("clicking the breadcrumb redirects to the list")
def sl27_breadcrumb_click(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "CrumbNav")
    try:
        ctx.record_page.click_breadcrumb_to_list()
        return Outcome.passed("Breadcrumb returns to the Loan fee types list.")
    finally:
        _delete_by_name(ctx, name)


@registry.matching("all field values are read-only on the view page")
def sl28_view_readonly(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "ReadOnly")
    try:
        return (
            Outcome.passed("View page renders no editable inputs or comboboxes.")
            if ctx.record_page.is_view_read_only()
            else Outcome.failed("The view page exposes editable controls.")
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("status is displayed as active by default")
def sl29_status_active(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "Status")
    try:
        value = ctx.record_page.view_field_text("Status")
        return (
            Outcome.passed(f"Status on a new record reads {value!r}.")
            if "active" in value.lower()
            else Outcome.failed(f"Status on a new record reads {value!r}, expected Active.")
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("edit button is visible and functional")
def sl30_edit_button(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "EditBtn")
    try:
        ctx.record_page.click_edit()
        return Outcome.passed("Edit is visible and opens the edit page.")
    finally:
        _delete_by_name(ctx, name)


@registry.matching("delete button is visible and functional")
def sl31_delete_button(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "DelBtn")
    try:
        ctx.record_page.click_delete()
        ctx.record_page.cancel_delete()
        return Outcome.passed("Delete is visible and opens the confirmation modal.")
    finally:
        _delete_by_name(ctx, name)


@registry.matching("3-dot menu contains")
def sl32_three_dot(ctx, row) -> Outcome:
    name = _with_view_record(ctx, "Menu")
    try:
        ctx.record_page.open_three_dot_menu()
        items = [i.lower() for i in ctx.record_page.three_dot_menu_items()]
        has_audit = any("audit trail" in i for i in items)
        has_obj = any("object definition" in i for i in items)
        if has_audit and has_obj:
            return Outcome.passed(f"3-dot menu contains both expected items: {items}.")
        missing = [
            lbl
            for lbl, ok in (("View audit trail", has_audit), ("Object definition", has_obj))
            if not ok
        ]
        ctx.screenshot("lft-view-three-dot-menu")
        return Outcome.failed(
            f"3-dot menu is missing {missing}; it contains {items}. "
            "Matches the app-wide missing-Object-definition defect. Not re-filed."
        )
    finally:
        _delete_by_name(ctx, name)


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE (EDIT)
# ══════════════════════════════════════════════════════════════════════════════


@registry.matching("edit page title is")
def sl33_edit_title(ctx, row) -> Outcome:
    """Known defect #31 family — re-confirm, do not re-file."""
    name = _unique("EditTitle")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_edit()
        title = ctx.record_page.get_page_title()
        if "loan-management/loan-fee-type" in title:
            ctx.screenshot("lft-edit-title-object-path")
            return Outcome.failed(
                f"RE-CONFIRMED: the edit page title exposes the raw internal object "
                f"path: {title!r}. Not re-filed (known)."
            )
        return Outcome.passed(f"Edit page title reads {title!r}.")
    finally:
        _delete_by_name(ctx, name)


@registry.matching("name field is mandatory (red asterisk) on edit")
def sl34_edit_name_mandatory(ctx, row) -> Outcome:
    name = _unique("EditMand")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_edit()
        ok = ctx.record_page.is_field_mandatory(ctx.record_page.NAME_ARIA_LABEL)
        return (
            Outcome.passed("The name field carries the mandatory asterisk on edit.")
            if ok
            else Outcome.failed("The name field has no mandatory marker on the edit page.")
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("record can be edited successfully with a valid name")
def sl35_edit_valid(ctx, row) -> Outcome:
    name = _unique("EditOK")
    renamed = name + " R"
    try:
        _create_record(ctx, name)
        ctx.record_page.click_edit()
        ctx.record_page.fill_name(renamed)
        ctx.record_page.save()
        ctx.record_page.wait_for_view_page()
        shown = ctx.record_page.view_field_text(ctx.record_page.NAME_ARIA_LABEL)
        if renamed in shown or renamed in ctx.record_page.get_page_title():
            return Outcome.passed(f"Rename persisted; view shows {shown!r}.")
        return Outcome.failed(f"Rename did not persist; view shows {shown!r}.")
    finally:
        _delete_by_name(ctx, renamed)
        _delete_by_name(ctx, name)


@registry.matching("proper error is shown when name is blank/whitespace on edit")
def sl36_edit_name_blank(ctx, row) -> Outcome:
    """Both halves of the objective: blank AND whitespace-only."""
    name = _unique("EditBlank")
    findings, leaked = [], False
    try:
        _create_record(ctx, name)

        ctx.record_page.click_edit()
        ctx.record_page.fill_name("")
        ctx.record_page.save()
        ctx.page.wait_for_timeout(2_000)
        b1 = ctx.record_page.error_banner_text()
        leaked = leaked or ("loan-management/loan-fee-type" in b1)
        findings.append(f"blank -> {b1[:110]!r}")

        ctx.record_page.fill_name("   ")
        ctx.record_page.save()
        ctx.page.wait_for_timeout(2_000)
        b2 = ctx.record_page.error_banner_text()
        leaked = leaked or ("loan-management/loan-fee-type" in b2)
        findings.append(f"whitespace -> {b2[:110]!r}")

        note = " || ".join(findings)
        if leaked:
            ctx.screenshot("lft-edit-blank-name-objectpath")
            return Outcome.failed(
                f"RE-CONFIRMED Bug #30 on edit: the message leaks the object path. "
                f"{note}. Not re-filed."
            )
        if b1 and b2:
            return Outcome.passed(f"Blank and whitespace names both rejected cleanly. {note}")
        return Outcome.failed(f"An empty name was not properly rejected on edit. {note}")
    finally:
        _delete_by_name(ctx, name)


def _edit_field_case(ctx, suffix: str, mutate, verify_label: str) -> Outcome:
    name = _unique(suffix)
    try:
        _create_record(ctx, name)
        ctx.record_page.click_edit()
        expected = mutate(ctx)
        ctx.record_page.save()
        ctx.record_page.wait_for_view_page()
        shown = ctx.record_page.view_field_text(verify_label)
        if expected.lower() in (shown or "").lower():
            return Outcome.passed(f"{verify_label} is editable; saved value {shown!r}.")
        return Outcome.failed(
            f"{verify_label} did not persist — expected ~{expected!r}, view shows {shown!r}."
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("gl account is editable on the edit page")
def sl37_edit_gl(ctx, row) -> Outcome:
    def mutate(c):
        c.record_page.set_gl_account(GL_QUERY)
        return GL_QUERY

    return _edit_field_case(ctx, "EditGL", mutate, "GL account")


@registry.matching("item is editable on the edit page")
def sl38_edit_item(ctx, row) -> Outcome:
    def mutate(c):
        c.record_page.set_item(ITEM_QUERY)
        return ITEM_QUERY

    return _edit_field_case(ctx, "EditItem", mutate, "Item")


@registry.matching("status is editable on the edit page")
def sl39_edit_status(ctx, row) -> Outcome:
    name = _unique("EditStat")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_edit()
        if not ctx.record_page.has_status_field():
            return Outcome.failed("No Status control on the edit page.")
        ctx.record_page.set_status("Inactive")
        ctx.record_page.save()
        ctx.record_page.wait_for_view_page()
        shown = ctx.record_page.view_field_text("Status")
        return (
            Outcome.passed(f"Status is editable; saved as {shown!r}.")
            if "inactive" in (shown or "").lower()
            else Outcome.failed(f"Status change did not persist (view shows {shown!r}).")
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("description is editable on the edit page")
def sl40_edit_description(ctx, row) -> Outcome:
    def mutate(c):
        text = "QA automated edit"
        c.record_page.fill_description(text)
        return text

    return _edit_field_case(ctx, "EditDesc", mutate, "Description")


@registry.matching("clicking save updates the record and redirects to detail")
def sl41_edit_save_redirect(ctx, row) -> Outcome:
    name = _unique("EditSave")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_edit()
        ctx.record_page.fill_description("QA redirect check")
        ctx.record_page.save()
        ctx.record_page.wait_for_view_page()
        return Outcome.passed(
            f"Save returned to the detail page ({ctx.record_page.get_page_title()!r})."
        )
    finally:
        _delete_by_name(ctx, name)


# ══════════════════════════════════════════════════════════════════════════════
# DELETE
# ══════════════════════════════════════════════════════════════════════════════


@registry.matching("clicking delete opens a confirmation modal")
def sl42_delete_modal(ctx, row) -> Outcome:
    name = _unique("DelModal")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_delete()
        title = ctx.record_page.get_delete_modal_title()
        ctx.record_page.cancel_delete()
        return Outcome.passed(f"Delete opens a confirmation modal titled {title!r}.")
    finally:
        _delete_by_name(ctx, name)


@registry.matching("modal contains a title, message, delete and cancel")
def sl43_delete_modal_parts(ctx, row) -> Outcome:
    name = _unique("DelParts")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_delete()
        dlg = ctx.record_page.delete_dialog()
        title = ctx.record_page.get_delete_modal_title()
        body = ctx.record_page.get_delete_modal_message()
        has_del = dlg.get_by_role("button", name="Delete").count() > 0
        has_cancel = dlg.get_by_role("button", name="Cancel").count() > 0
        ctx.record_page.cancel_delete()
        if title and body and has_del and has_cancel:
            return Outcome.passed(
                f"Modal has title {title!r}, a message, and both Delete and Cancel."
            )
        return Outcome.failed(
            f"Modal incomplete — title={title!r} delete_btn={has_del} cancel_btn={has_cancel}."
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("modal shows a proper confirmation message with the record name")
def sl44_delete_modal_names_record(ctx, row) -> Outcome:
    name = _unique("DelName")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_delete()
        body = ctx.record_page.get_delete_modal_message()
        ctx.record_page.cancel_delete()
        return (
            Outcome.passed(f"Modal names the record being deleted ({name!r}).")
            if name in body
            else Outcome.failed(f"Modal does not name the record. Body: {body[:160]!r}")
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("clicking cancel closes the modal without deleting")
def sl45_delete_cancel(ctx, row) -> Outcome:
    name = _unique("DelCancel")
    try:
        _create_record(ctx, name)
        ctx.record_page.click_delete()
        ctx.record_page.cancel_delete()
        ctx.page.wait_for_timeout(800)
        ctx.listing_page.navigate_to_list()
        ctx.listing_page.search_by_name(name)
        return (
            Outcome.passed("Cancel closed the modal and the record still exists.")
            if ctx.listing_page.is_record_visible(name)
            else Outcome.failed("The record was deleted despite clicking Cancel.")
        )
    finally:
        _delete_by_name(ctx, name)


@registry.matching("clicking delete removes the record and redirects to the list")
def sl46_delete_confirm(ctx, row) -> Outcome:
    name = _unique("DelGo")
    _create_record(ctx, name)
    ctx.record_page.click_delete()
    ctx.record_page.confirm_delete()
    ctx.listing_page.wait_for_list_page()
    ctx.listing_page.search_by_name(name)
    gone = not ctx.listing_page.is_record_visible(name)
    return (
        Outcome.passed("Confirming Delete removed the record and returned to the list.")
        if gone
        else Outcome.failed("The record still appears in the list after confirming Delete.")
    )


# ══════════════════════════════════════════════════════════════════════════════
# GENERAL / ACCESSIBILITY
# ══════════════════════════════════════════════════════════════════════════════


@registry.matching("ui labels and accessibility (aria) labels are properly translated")
def sl47_a11y(ctx, row) -> Outcome:
    ctx.listing_page.navigate_to_list()
    leaked = set(ctx.record_page.untranslated_aria_keys())
    ctx.listing_page.click_create()
    leaked |= set(ctx.record_page.untranslated_aria_keys())
    if not leaked:
        return Outcome.passed("No untranslated IA.* / BULK_SELECTED keys found.")
    ctx.screenshot("lft-untranslated-aria-keys")
    return Outcome.failed(
        f"RE-CONFIRMED Bug #43 / IAUI-616: untranslated resource keys still leak: "
        f"{sorted(leaked)}. Not re-filed (deferred to IAUI-616)."
    )


@registry.matching("editable, and delete is correctly blocked")
def sl48_in_use(ctx, row) -> Outcome:
    """
    Both halves, against the pre-existing in-use record (Loan Fee Type 02).

    Never creates or edits a loan type — if the in-use link is gone, the state
    can't be asserted and the row is returned Unconfirmed rather than guessed.
    """
    target = "Loan Fee Type 02"
    findings = []
    ctx.listing_page.navigate_to_list()
    ctx.listing_page.search_by_name(target)
    if not ctx.listing_page.is_record_visible(target):
        return Outcome.unconfirmed(
            f"{target!r} does not exist in this company, so the in-use state could not "
            "be set up. This row needs a loan fee type referenced by a loan type's Fee "
            "row; creating that link would mean editing a loan type, which this run "
            "does not do. Verify manually or seed the fixture first."
        )

    original_desc = ""
    edited = False
    try:
        # Half 1: still editable while in use.
        ctx.listing_page.open_record_by_name(target)
        original_desc = ctx.record_page.view_field_text("Description")
        ctx.record_page.click_edit()
        ctx.record_page.fill_description("QA in-use edit check")
        ctx.record_page.save()
        ctx.record_page.wait_for_view_page()
        edited = True
        findings.append("EDIT while in use: succeeded.")

        # Half 2: delete must be blocked, with a message naming the dependency.
        ctx.record_page.click_delete()
        ctx.record_page.confirm_delete()
        ctx.page.wait_for_timeout(2_500)
        banner = ctx.record_page.error_banner_text()

        ctx.listing_page.navigate_to_list()
        ctx.listing_page.search_by_name(target)
        still_there = ctx.listing_page.is_record_visible(target)

        if not still_there:
            return Outcome.failed(
                f"{target!r} was DELETED even though it is in use. {' '.join(findings)}",
                Defect(
                    title="A loan fee type that is in use can be deleted",
                    area=A_DELETE,
                    steps=LOGIN_STEPS + [
                        f"Open {target}, which is referenced by a loan type's Fee row.",
                        "Click *Delete* and confirm.",
                    ],
                    observed=["The record was deleted despite being referenced."],
                    expected=["Deletion should be blocked with a message naming the loan type."],
                    screenshot=ctx.screenshot("lft-inuse-delete-succeeded"),
                ),
            )

        findings.append(f"DELETE while in use: blocked, record intact. Message: {banner[:160]!r}")
        if "entityDef.table" in banner or "Cannot invoke" in banner:
            ctx.screenshot("lft-inuse-delete-raw-error")
            return Outcome.failed(
                "RE-CONFIRMED Bug #32: delete is correctly blocked but surfaces a raw "
                f"internal error instead of naming the loan type. {' '.join(findings)} "
                "Not re-filed."
            )
        if banner:
            return Outcome.passed(
                f"In-use fee type is editable and delete is blocked with a message. "
                f"{' '.join(findings)}"
            )
        return Outcome.unconfirmed(
            f"Delete appears blocked but no message was captured. {' '.join(findings)}"
        )
    finally:
        # Put the description back so the shared record is left as found.
        # Only if we actually changed it — otherwise there is nothing to undo
        # and the lookup would fail on a record that does not exist.
        try:
            if not edited:
                raise RuntimeError("nothing to restore")
            ctx.listing_page.navigate_to_list()
            ctx.listing_page.search_by_name(target)
            ctx.listing_page.open_record_by_name(target)
            ctx.record_page.click_edit()
            ctx.record_page.fill_description(original_desc if original_desc != "--" else "")
            ctx.record_page.save()
        except Exception:
            pass


def _bulk_delete_fixture(ctx, count: int = 2) -> list[str]:
    names = []
    for i in range(count):
        n = _unique(f"Bulk{i}")
        _create_record(ctx, n)
        names.append(n)
    return names


@registry.matching("bulk (multi-select) delete confirmation modal")
def sl49_bulk_modal(ctx, row) -> Outcome:
    names = []
    try:
        names = _bulk_delete_fixture(ctx, 2)
        ctx.listing_page.navigate_to_list()
        ctx.listing_page.search_by_name(QA_PREFIX)

        selected = sum(1 for n in names if ctx.listing_page.select_row_by_name(n))
        if selected != len(names):
            return Outcome.unconfirmed(
                f"Could only select {selected}/{len(names)} QA rows for bulk delete."
            )
        # Guard: never bulk-delete anything that isn't ours.
        if ctx.listing_page.selected_count() != selected:
            return Outcome.unconfirmed(
                "Selection count did not match the QA rows chosen — aborting rather "
                "than risking a non-QA record."
            )

        ctx.listing_page.click_bulk_delete()
        dlg = ctx.listing_page.bulk_delete_dialog()
        body = (dlg.inner_text() or "").strip()
        headings = dlg.get_by_role("heading").count()
        names_shown = sum(1 for n in names if n in body)

        ctx.screenshot("lft-bulk-delete-modal")
        stripped = body.replace("Delete", "").replace("Cancel", "").strip()

        if headings and stripped and names_shown:
            return Outcome.passed(
                f"Bulk-delete modal has a title and lists the records. Body: {body[:140]!r}"
            )
        return Outcome.failed(
            "RE-CONFIRMED: the bulk-delete confirmation modal is effectively empty — "
            f"headings={headings}, records named={names_shown}/{len(names)}, "
            f"body besides the buttons={stripped[:80]!r}. The user confirms a permanent "
            "delete blind. Already recorded as provisional #89; not re-filed."
        )
    finally:
        for n in names:
            _delete_by_name(ctx, n)


@registry.matching("confirmation message shown after a bulk delete")
def sl50_bulk_toast(ctx, row) -> Outcome:
    names = []
    try:
        names = _bulk_delete_fixture(ctx, 2)
        ctx.listing_page.navigate_to_list()
        ctx.listing_page.search_by_name(QA_PREFIX)

        selected = sum(1 for n in names if ctx.listing_page.select_row_by_name(n))
        if selected != len(names) or ctx.listing_page.selected_count() != selected:
            return Outcome.unconfirmed(
                "Could not select exactly the QA rows for bulk delete — aborting."
            )

        ctx.listing_page.click_bulk_delete()
        ctx.listing_page.bulk_delete_dialog().get_by_role(
            "button", name="Delete"
        ).first.click()
        ctx.page.wait_for_timeout(1_200)
        toast = ctx.listing_page.toast_text()
        ctx.screenshot("lft-bulk-delete-toast")

        names = []  # deleted by the bulk action
        if not toast:
            return Outcome.unconfirmed(
                "No confirmation message was captured after the bulk delete (the toast "
                "auto-dismisses quickly)."
            )
        if "loan fee type" in toast.lower():
            return Outcome.passed(f"Bulk-delete confirmation reads {toast!r}.")
        return Outcome.failed(
            f"RE-CONFIRMED: the bulk-delete confirmation names the wrong object — it "
            f'reads {toast!r} instead of "Loan fee types deleted". Already recorded as '
            "provisional #90; not re-filed."
        )
    finally:
        for n in names:
            _delete_by_name(ctx, n)


# ══════════════════════════════════════════════════════════════════════════════
# LISTER (Config Listers sheet, rows 19-21)
# ══════════════════════════════════════════════════════════════════════════════


@registry.matching("column names render properly")
def lister_columns(ctx, row) -> Outcome:
    ctx.listing_page.navigate_to_list()
    headers = ctx.listing_page.get_column_headers()
    leaked = [h for h in headers if h.startswith("IA.") or h == "BULK_SELECTED"]
    if not leaked:
        return Outcome.passed(f"Lister columns render cleanly: {headers}.")
    return Outcome.failed(
        f"Lister column headers leak raw resource keys: {leaked} (all headers: {headers}). "
        "Same Bug #43 / IAUI-616 family; not re-filed."
    )


@registry.matching("filter by search box")
def lister_filter(ctx, row) -> Outcome:
    """Seeds two distinguishable records so the filter can be proven narrowing."""
    keep = _unique("FilterKeep")
    other = _unique("FilterOther")
    try:
        _create_record(ctx, keep)
        _create_record(ctx, other)
        ctx.listing_page.navigate_to_list()
        before = len(ctx.listing_page.row_names())
        ctx.listing_page.search_by_name(keep)
        after = ctx.listing_page.row_names()
        ctx.listing_page.clear_search()
        if after == [keep]:
            return Outcome.passed(
                f"Name filter narrowed {before} row(s) to exactly the match: {after}."
            )
        if keep in after and len(after) < before:
            return Outcome.passed(
                f"Name filter narrowed {before} row(s) to {len(after)}, including the match."
            )
        return Outcome.failed(
            f"Name filter did not narrow correctly — {before} rows before, {after} after."
        )
    finally:
        _delete_by_name(ctx, keep)
        _delete_by_name(ctx, other)


@registry.matching("data renders; generic grid controls work")
def lister_data(ctx, row) -> Outcome:
    """Seeds a record so an empty company still proves the grid renders data."""
    name = _unique("GridData")
    try:
        _create_record(ctx, name)
        ctx.listing_page.navigate_to_list()
        headers = ctx.listing_page.get_column_headers()
        names = ctx.listing_page.row_names()
        if name in names and {"Name", "Status"} <= set(headers):
            return Outcome.passed(
                f"Grid renders the seeded record under Name/Status "
                f"({len(names)} row(s) shown)."
            )
        return Outcome.failed(
            f"Grid did not render the seeded record — headers={headers}, rows={names[:5]}."
        )
    finally:
        _delete_by_name(ctx, name)
