"""
test_view_and_delete.py
==================================
Playwright / pytest tests for the VIEW and DELETE lifecycle stages of the
Loan Type module (Lending Management → Setup → Loan type).

Test IDs: TC-LT-015 – TC-LT-027 (View), TC-LT-059 – TC-LT-063 (Delete, new —
not present in the original spreadsheet), TC-LT-079 – TC-LT-084 (new — added
to reach full parity with the "Loan Type - CRUD" checklist sheet in
LME_Regression_Consolidated.xlsx, 2026-08-17).
Selectors/flows verified against live DOM 2026-07-15.
  * View heading  : "Loan type: <ID>" (no name in the heading, unlike
                     Depository Account Category's "<ID>--<Name>" pattern)
  * Delete modal  : "Delete loan type" — same framework component as
                     Depository Account Category's delete modal, including its
                     zero-bounding-box quirk on the dialog wrapper (see
                     LoanTypePage._delete_dialog).

TC-LT-079–084 close remaining View/Delete checklist items: the 3-dot menu's
missing "Object definition" entry (KNOWN DEFECT — checklist row 131/133),
field read-only/non-editable enforcement, page footer content, and an
explicit (not merely fixture-teardown-implied) delete-of-an-unassigned-record
assertion for checklist row 213.
"""

import pytest
from playwright.sync_api import expect

from pages.loan_type.listing_page import LoanTypeListingPage
from pages.loan_type.type_page import LoanTypePage


@pytest.fixture()
def view_page(created_loan_type, loan_type_listing_page, steps):
    """Open the View page for a pre-created loan type. Returns (page_obj, name)."""
    listing: LoanTypeListingPage = loan_type_listing_page
    name: str = created_loan_type
    listing.navigate_to_list()
    listing.search_by_name(name)
    listing.open_record_by_name(name)
    steps.append(f"Opened View page for '{name}'")
    return LoanTypePage(listing.page), name


class TestViewLoanType:

    def test_the_view_page_displays_the_loan_type_name(self, view_page, steps):
        """TC-LT-015 — Detail page displays the Loan type name."""
        cat, name = view_page
        steps.append(f"Checked page for name '{name}'")
        expect(cat.frame.get_by_text(name, exact=True).first).to_be_visible()

    def test_the_view_page_displays_the_type_value(self, view_page, steps):
        """TC-LT-016 — Detail page displays Type (Revolving/Non-revolving)."""
        cat, _ = view_page
        steps.append("Checked page for the Type field value")
        expect(cat.frame.get_by_text("Revolving", exact=True).first).to_be_visible()

    def test_the_view_page_displays_the_interest_type_value(self, view_page, steps):
        """TC-LT-017 — Detail page displays Interest type."""
        cat, _ = view_page
        steps.append("Checked page for the Interest type field value")
        expect(cat.frame.get_by_text("Compound", exact=True).first).to_be_visible()

    def test_the_view_page_displays_the_interest_calculation_method_value(self, view_page, steps):
        """TC-LT-018 — Detail page displays Interest calculation method."""
        cat, _ = view_page
        steps.append("Checked page for the Interest calculation method field value")
        expect(cat.frame.get_by_text("Actual/365", exact=True).first).to_be_visible()

    def test_the_view_page_shows_status_active(self, view_page, steps):
        """TC-LT-019 — Detail page shows Status = Active."""
        cat, _ = view_page
        steps.append("Checked page for Status = Active")
        expect(cat.frame.get_by_text("Active", exact=True).first).to_be_visible()

    def test_the_loan_invoicing_defaults_section_is_visible(self, view_page, steps):
        """TC-LT-020 — 'Loan invoicing defaults' section is visible."""
        cat, _ = view_page
        steps.append("Checked for the 'Loan invoicing defaults' section heading")
        expect(cat.frame.get_by_text("Loan invoicing defaults", exact=True).first).to_be_visible()

    def test_the_payment_priority_order_section_is_visible(self, view_page, steps):
        """TC-LT-021 — 'Payment priority order' section is visible."""
        cat, _ = view_page
        steps.append("Checked for the 'Payment priority order' section heading")
        expect(cat.frame.get_by_text("Payment priority order", exact=True).first).to_be_visible()

    def test_the_payment_priority_grid_has_sort_order_type_and_fee_type_columns_on_view(self, view_page, steps):
        """TC-LT-022 — Payment priority grid has Sort order, Type, Fee type columns."""
        cat, _ = view_page
        steps.append("Checked Payment priority order grid column headers")
        headers = cat.frame.get_by_role("columnheader")
        text = " ".join(h.inner_text() for h in headers.all()).lower()
        assert "sort order" in text
        assert "type" in text
        assert "fee type" in text

    def test_the_edit_button_is_visible_on_the_detail_page(self, view_page, steps):
        """TC-LT-023 — Edit button is visible on the detail page."""
        cat, _ = view_page
        steps.append("Checked header for Edit button")
        expect(cat.frame.get_by_role("button", name="Edit")).to_be_visible()

    def test_the_delete_button_is_visible_on_the_detail_page(self, view_page, steps):
        """TC-LT-024 — Delete button is visible on the detail page."""
        cat, _ = view_page
        steps.append("Checked header for Delete button")
        expect(cat.frame.get_by_role("button", name="Delete")).to_be_visible()

    def test_the_three_dot_menu_contains_view_audit_trail(self, view_page, steps):
        """TC-LT-025 — Three-dot menu shows 'View audit trail'."""
        cat, _ = view_page
        steps.append("Opened header More actions, then the nested three-dot menu")
        cat.open_view_three_dot_menu()
        expect(cat.frame.get_by_role("button", name="View audit trail")).to_be_visible()

    def test_the_loan_types_breadcrumb_link_navigates_back_to_the_list(self, view_page, steps):
        """TC-LT-026 — Breadcrumb 'Loan types' link navigates back to the list."""
        cat, _ = view_page
        steps.append("Clicked the 'Loan types' breadcrumb link")
        cat.click_back_to_list()
        expect(
            cat.frame.get_by_role("heading", name="Loan types")
        ).to_be_visible()

    def test_the_back_arrow_navigates_to_the_loan_types_list(self, view_page, steps):
        """TC-LT-027 — Back arrow navigates to the Loan types list."""
        cat, _ = view_page
        steps.append("Clicked the 'Back to previous page' arrow")
        cat.frame.get_by_role("button", name="Back to previous page").first.click()
        expect(
            cat.frame.get_by_role("heading", name="Loan types")
        ).to_be_visible()

    def test_the_three_dot_menu_is_missing_the_object_definition_entry(self, view_page, steps):
        """TC-LT-079 [new; KNOWN DEFECT] — The three-dot 'More actions' menu on
        the View page is documented as offering "View audit trail" AND
        "Object definition" (checklist row 131), but the checklist's own
        execution found "Object definition" absent. This test asserts the
        documented/expected behaviour and is expected to fail until that
        defect is fixed — see Jira Bug #34 / IADSSL-1725 in the Loan Type
        findings (checklist rows 131/133). Uses the same
        open_view_three_dot_menu() + direct role="button" visibility check
        pattern as the pre-existing, live-verified TC-LT-025, rather than
        get_three_dot_menu_items() (that helper's role="dialog" lookup did
        not match this menu's actual markup in live testing 2026-08-17)."""
        cat, _ = view_page
        steps.append("Opened the View page three-dot menu")
        cat.open_view_three_dot_menu()
        assert cat.frame.get_by_role("button", name="Object definition").count() > 0, (
            "'Object definition' missing from the three-dot menu (known defect "
            "— Bug #34 / IADSSL-1725)"
        )

    def test_loan_type_information_fields_are_not_editable_on_the_view_page(self, view_page, steps):
        """TC-LT-080 [new] — Loan type information fields render as read-only
        text on the View page — no live input controls (checklist row 154).
        Checked page-wide rather than scoped to the section container: the
        View page has no other section with form-style inputs to worry
        about (Payment priority order is a grid, covered separately by
        TC-LT-081), so this is an equivalent, DOM-structure-independent
        check."""
        cat, _ = view_page
        steps.append("Checked the whole View page for editable text/select controls")
        inputs = cat.frame.locator(
            "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), textarea, select"
        )
        assert inputs.count() == 0, (
            f"Expected 0 editable input controls on the View page, found "
            f"{inputs.count()}"
        )

    def test_the_payment_priority_grid_is_read_only_on_the_view_page(self, view_page, steps):
        """TC-LT-081 [new] — Payment priority order grid is read-only on the
        View page: no 'Add row' button and no per-row Remove control
        (checklist row 155)."""
        cat, _ = view_page
        steps.append("Checked the Payment priority order grid for Add/Remove row controls")
        expect(cat.frame.get_by_role("button", name="Add row")).to_have_count(0)
        expect(cat.frame.get_by_role("button", name="Remove row")).to_have_count(0)

    def test_the_page_footer_shows_a_privacy_policy_link_and_copyright_text(self, view_page, steps):
        """TC-LT-082 [new] — Page footer shows a 'Privacy policy' link and
        copyright text (checklist row 159). The footer is rendered on the
        outer app chrome, not inside the module content iframe (confirmed
        live 2026-08-17 — visible on screen but not reachable via
        cat.frame), so this checks the top-level page rather than the
        module iframe."""
        cat, _ = view_page
        steps.append("Checked the page footer (outer app chrome, outside the module iframe)")
        expect(cat.page.get_by_text("Privacy policy", exact=False).first).to_be_visible()
        expect(cat.page.get_by_text("Copyright", exact=False).first).to_be_visible()

    def test_the_view_page_data_matches_the_values_entered_during_creation(self, view_page, steps):
        """TC-LT-083 [new] — View page data matches exactly what was entered
        during creation (checklist row 162 — covers name, Type, Interest
        type and Interest calculation method, the values the
        `created_loan_type` fixture sets)."""
        cat, name = view_page
        steps.append(f"Checked View page reflects the created record's saved values for '{name}'")
        expect(cat.frame.get_by_text(name, exact=True).first).to_be_visible()
        expect(cat.frame.get_by_text("Revolving", exact=True).first).to_be_visible()
        expect(cat.frame.get_by_text("Compound", exact=True).first).to_be_visible()
        expect(cat.frame.get_by_text("Actual/365", exact=True).first).to_be_visible()


class TestDeleteLoanType:

    def test_clicking_delete_opens_the_confirmation_modal(self, loan_type_for_delete, loan_type_listing_page, steps):
        """TC-LT-059 [new] — Clicking Delete opens the confirmation modal."""
        listing = loan_type_listing_page
        listing.open_record_by_name(loan_type_for_delete)
        cat = LoanTypePage(listing.page)
        steps.append(f"Opened View page for '{loan_type_for_delete}', clicked Delete")
        cat.click_delete()
        expect(cat.frame.get_by_role("heading", name=cat.DELETE_DIALOG).last).to_be_visible()
        cat.confirm_delete_in_modal()  # cleanup

    def test_the_delete_modal_message_names_the_record_and_says_it_will_be_deleted(self, loan_type_for_delete, loan_type_listing_page, steps):
        """TC-LT-060 [new] — Modal message names the record and says it will be deleted."""
        listing = loan_type_listing_page
        listing.open_record_by_name(loan_type_for_delete)
        cat = LoanTypePage(listing.page)
        steps.append(f"Opened View page for '{loan_type_for_delete}', clicked Delete")
        cat.click_delete()
        message = cat.get_delete_modal_message()
        assert loan_type_for_delete in message, f"Expected '{loan_type_for_delete}' in: '{message}'"
        assert "will be permanently deleted" in message.lower(), f"Missing deletion notice in: '{message}'"
        cat.confirm_delete_in_modal()

    def test_confirming_delete_permanently_removes_the_record_from_the_list(self, loan_type_for_delete, loan_type_listing_page, steps):
        """TC-LT-061 [new] — Confirming Delete removes the record from the list."""
        listing: LoanTypeListingPage = loan_type_listing_page
        name = loan_type_for_delete

        listing.open_record_by_name(name)
        cat = LoanTypePage(listing.page)
        steps.append(f"Opened View page for '{name}'")
        cat.click_delete()
        steps.append("Clicked Delete, confirmed in modal")
        cat.confirm_delete_in_modal()

        listing.wait_for_list_page()
        listing.search_by_name(name)
        steps.append(f"Filtered list by '{name}' to verify removal")
        assert not listing.is_record_visible(name), f"Record '{name}' should have been deleted"

    def test_clicking_cancel_in_the_modal_closes_it_without_deleting_the_record(self, loan_type_for_delete, loan_type_listing_page, steps):
        """TC-LT-062 [new] — Cancel in the modal closes it without deleting."""
        listing = loan_type_listing_page
        name = loan_type_for_delete

        listing.open_record_by_name(name)
        cat = LoanTypePage(listing.page)
        steps.append(f"Opened View page for '{name}', clicked Delete then Cancel")
        cat.click_delete()
        cat.cancel_delete_in_modal()

        expect(cat.frame.get_by_role("heading", name=cat.DELETE_DIALOG).last).not_to_be_visible()
        expect(cat.frame.locator("h1").filter(has_text="Loan type:")).to_be_visible()

        # Cleanup: now actually delete it.
        cat.click_delete()
        cat.confirm_delete_in_modal()

    def test_deleting_from_the_view_page_redirects_to_the_loan_types_list(self, loan_type_for_delete, loan_type_listing_page, steps):
        """TC-LT-063 [new] — Deleting from the View page redirects to the Loan types list."""
        listing = loan_type_listing_page
        name = loan_type_for_delete

        listing.open_record_by_name(name)
        cat = LoanTypePage(listing.page)
        steps.append(f"Opened View page for '{name}', clicked Delete and confirmed")
        cat.click_delete()
        cat.confirm_delete_in_modal()

        expect(
            cat.frame.get_by_role("heading", name="Loan types")
        ).to_be_visible()

    def test_a_loan_type_not_assigned_to_any_loan_account_deletes_successfully(
        self, loan_type_for_delete, loan_type_listing_page, steps
    ):
        """TC-LT-084 [new] — A Loan type not assigned to any loan account
        deletes successfully via the standard 'Delete loan type' confirmation
        (checklist row 213). `loan_type_for_delete` is created fresh for this
        test and is guaranteed unassigned, so a clean delete-and-verify here
        is direct evidence for that checklist item, distinct from
        TC-LT-061 which only checks the record disappears from the list."""
        listing = loan_type_listing_page
        name = loan_type_for_delete

        listing.open_record_by_name(name)
        cat = LoanTypePage(listing.page)
        steps.append(f"Opened View page for unassigned Loan type '{name}'")
        cat.click_delete()
        message = cat.get_delete_modal_message()
        steps.append("Clicked Delete; confirmation modal did not warn about an assignment conflict")
        assert "cannot" not in message.lower() and "assigned" not in message.lower(), (
            f"Unexpected assignment-conflict wording in delete confirmation for "
            f"an unassigned record: '{message}'"
        )
        cat.confirm_delete_in_modal()
        steps.append("Confirmed delete")
        listing.wait_for_list_page()
        listing.search_by_name(name)
        assert not listing.is_record_visible(name), (
            f"Unassigned Loan type '{name}' should delete successfully and no "
            f"longer appear in the list"
        )
