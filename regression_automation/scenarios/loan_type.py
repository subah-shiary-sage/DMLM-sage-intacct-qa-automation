"""
Verdict handlers for the Loan Type checklist.

Each handler runs one checklist row against the live app and returns an Outcome.
Rows with no handler are reported as unhandled and left untouched in the
workbook — they still need a human.

Handlers here are deliberately read-only (they inspect existing records rather
than creating them) so a run leaves no test data behind.
"""

from __future__ import annotations

from . import Defect, Outcome, ScenarioRegistry

registry = ScenarioRegistry("loan_type")

AREA_VIEW = "Lending Management > Loan type > View"
AREA_EDIT = "Lending Management > Loan type > Edit"
AREA_CREATE = "Lending Management > Loan type > Create"


def _first_record(ctx) -> str | None:
    """Name of the first loan type in the lister, or None if the list is empty."""
    links = ctx.listing_page.frame.get_by_role("link")
    for i in range(min(links.count(), 40)):
        text = (links.nth(i).inner_text() or "").strip()
        if text and text.lower() not in ("create", "loan types"):
            return text
    return None


@registry.matching("section is collapsed by default")
def section_collapsed_by_default(ctx, row) -> Outcome:
    steps = [
        "Log in and switch to the Lending Management Entity.",
        "Navigate to Lending Management > Setup > Loan type.",
        "Click *Create*.",
        "Observe the state of each section on the create form.",
    ]
    ctx.listing_page.navigate_to_list()
    ctx.listing_page.click_create()

    expanded = ctx.record_page.is_section_expanded()
    if not expanded:
        return Outcome.passed(
            "Section is collapsed by default on the create page.", steps
        )

    shot = ctx.screenshot("loan-type-create-section-expanded-by-default")
    return Outcome.failed(
        "Section is EXPANDED by default on the create page, not collapsed.",
        Defect(
            title="The create form's section is expanded by default instead of collapsed",
            area=AREA_CREATE,
            steps=steps,
            observed=["The section is already expanded when the create form opens."],
            expected=["The section should be collapsed by default, per the checklist."],
            screenshot=shot,
        ),
        steps,
    )


@registry.matching('opens a menu with "view audit trail"', "object definition" )
def three_dot_menu_contents(ctx, row) -> Outcome:
    steps = [
        "Log in and switch to the Lending Management Entity.",
        "Navigate to Lending Management > Setup > Loan type.",
        "Open any loan type record.",
        'Click the "..." (More actions) control in the header.',
    ]
    ctx.listing_page.navigate_to_list()
    name = _first_record(ctx)
    if not name:
        return Outcome.unconfirmed(
            "No loan type records exist in this entity, so the View page could not be reached."
        )

    ctx.listing_page.open_record_by_name(name)
    ctx.record_page.open_view_three_dot_menu()
    items = [i.strip().lower() for i in ctx.record_page.get_three_dot_menu_items()]

    has_audit = any("audit trail" in i for i in items)
    has_objdef = any("object definition" in i for i in items)

    if has_audit and has_objdef:
        return Outcome.passed(
            f'The "..." menu contains both expected items: {items}.', steps
        )

    missing = [
        label
        for label, present in (("View audit trail", has_audit), ("Object definition", has_objdef))
        if not present
    ]
    shot = ctx.screenshot("loan-type-view-three-dot-menu")
    return Outcome.failed(
        f'The "..." menu is missing: {", ".join(missing)}. Present: {items}.',
        Defect(
            title=(
                'The View page "More actions" menu is missing the '
                f'{" and ".join(missing)} option'
            ),
            area=AREA_VIEW,
            steps=steps,
            observed=[
                f'The menu contains only: {", ".join(items) or "(nothing)"}.',
                f'Missing: {", ".join(missing)}.',
            ],
            expected=[
                'The menu should offer both "View audit trail" and "Object definition".'
            ],
            screenshot=shot,
        ),
        steps,
    )


@registry.matching("page title displays as \"edit loan-type")
def edit_page_title_format(ctx, row) -> Outcome:
    steps = [
        "Log in and switch to the Lending Management Entity.",
        "Navigate to Lending Management > Setup > Loan type.",
        "Open any loan type record and click *Edit*.",
        "Read the page title.",
    ]
    ctx.listing_page.navigate_to_list()
    name = _first_record(ctx)
    if not name:
        return Outcome.unconfirmed(
            "No loan type records exist in this entity, so the Edit page could not be reached."
        )

    ctx.listing_page.open_record_by_name(name)
    ctx.record_page.click_edit()
    title = ctx.record_page.get_page_title().strip()

    # The defect is the raw internal object path leaking into the heading.
    if "loan-management/loan-type" in title:
        shot = ctx.screenshot("loan-type-edit-title-object-path")
        return Outcome.failed(
            f"The edit page title exposes the internal object path: {title!r}.",
            Defect(
                title="The Edit page title exposes the raw internal object path",
                area=AREA_EDIT,
                steps=steps,
                observed=[
                    f"The heading reads {{{{{title}}}}}.",
                    "It shows the internal object path instead of a readable label.",
                ],
                expected=[
                    'The heading should read "Edit loan type: <ID>--<name>" without '
                    "the internal object path."
                ],
                screenshot=shot,
            ),
            steps,
        )

    return Outcome.passed(f"Edit page title reads {title!r}.", steps)
