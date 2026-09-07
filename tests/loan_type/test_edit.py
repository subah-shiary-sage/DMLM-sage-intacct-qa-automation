"""
test_edit.py
=======================
Playwright / pytest tests for the EDIT lifecycle stage of the Loan Type
module (Lending Management → Setup → Loan type).

Test IDs: TC-LT-047 – TC-LT-056, TC-LT-085 – TC-LT-092 (new — added to reach
full parity with the "Loan Type - CRUD" checklist sheet in
LME_Regression_Consolidated.xlsx, 2026-08-17).
Selectors/flows verified against live DOM 2026-07-15.
Edit heading is "Edit loan-management/loan-type: <ID>--<Name>" (includes an
internal module-path prefix, unlike the View/Create heading format).

TC-LT-085–092 close remaining Edit checklist items: the friendly-title
KNOWN DEFECT (checklist row 164 — see also TEST_CASES_Loan_Type.md's
existing note on this heading format), Status dropdown option content,
mandatory-marker parity between Create and Edit for "Interest type"
(checklist item E1/F11 — a documented MISMATCH), and the revolving/
non-revolving Payment priority row-composition rules re-checked on Edit
(checklist rows 207/208, distinct from the Create-page versions
TC-LT-064/065).
"""

import pytest
from playwright.sync_api import expect

from pages.loan_type.listing_page import LoanTypeListingPage
from pages.loan_type.type_page import LoanTypePage


@pytest.fixture()
def edit_form(created_loan_type, loan_type_listing_page, steps):
    """Open the Edit form for the pre-created loan type. Returns (page_obj, name)."""
    listing: LoanTypeListingPage = loan_type_listing_page
    original_name: str = created_loan_type

    listing.navigate_to_list()
    listing.search_by_name(original_name)
    listing.open_record_by_name(original_name)
    cat = LoanTypePage(listing.page)
    cat.click_edit()
    steps.append(f"Opened Edit form for '{original_name}'")
    return cat, original_name


class TestEditLoanType:

    def test_the_edit_form_pre_populates_the_loan_type_name(self, edit_form, steps):
        """TC-LT-047 — Edit form pre-populates the Loan type name."""
        cat, original_name = edit_form
        steps.append("Checked the Loan type name field's current value")
        assert cat.get_name_value() == original_name

    def test_the_edit_form_pre_populates_the_description_and_keeps_it_editable(self, edit_form, steps):
        """TC-LT-048 — Edit form pre-populates Description (empty in this fixture's data)."""
        cat, _ = edit_form
        steps.append("Checked the Description field is present and editable")
        expect(cat.frame.locator(cat.DESCRIPTION_INPUT).first).to_be_editable()

    def test_the_type_field_is_read_only_plain_text_in_edit_mode(self, edit_form, steps):
        """TC-LT-049 — Type field is read-only in edit mode (plain text, not a radio)."""
        cat, _ = edit_form
        steps.append("Checked that no Type radio buttons are present on the Edit form")
        expect(cat.frame.get_by_role("radio", name="Revolving", exact=True)).to_have_count(0)
        expect(cat.frame.get_by_text("Revolving", exact=True).first).to_be_visible()

    def test_the_edit_form_pre_populates_the_interest_type(self, edit_form, steps):
        """TC-LT-050 — Edit form pre-populates Interest type."""
        cat, _ = edit_form
        steps.append("Checked the Interest type combobox's current value")
        combo = cat.frame.get_by_role("combobox", name="Interest type").first
        expect(combo).to_contain_text("Compound")

    def test_the_edit_form_pre_populates_the_interest_calculation_method(self, edit_form, steps):
        """TC-LT-051 — Edit form pre-populates Interest calculation method."""
        cat, _ = edit_form
        steps.append("Checked the Interest calculation method combobox's current value")
        combo = cat.frame.get_by_role("combobox", name="Interest calculation method").first
        expect(combo).to_contain_text("Actual/365")

    def test_the_edit_form_pre_populates_the_status(self, edit_form, steps):
        """TC-LT-052 — Edit form pre-populates Status."""
        cat, _ = edit_form
        steps.append("Checked the Status combobox's current value")
        combo = cat.frame.get_by_role("combobox", name="Status").first
        expect(combo).to_contain_text("Active")

    def test_clearing_the_loan_type_name_and_saving_keeps_the_user_in_edit_mode(self, edit_form, steps):
        """TC-LT-053 — Clearing Loan type name and saving keeps the user in Edit mode."""
        cat, _ = edit_form
        steps.append("Cleared the Loan type name field")
        cat.fill_name("")
        cat.save()
        steps.append("Clicked Save with an empty name")
        cat.page.wait_for_timeout(1_500)
        expect(
            cat.frame.locator("h1").filter(has_text="Edit").filter(has_text="loan-type")
        ).to_be_visible()

    def test_cancelling_the_edit_does_not_save_changes_and_retains_the_original_name(self, edit_form, steps):
        """TC-LT-054 — Cancelling edit does not save changes; original name is retained."""
        cat, original_name = edit_form
        steps.append("Changed the Loan type name to 'CHANGED_NAME'")
        cat.fill_name("CHANGED_NAME")
        cat.cancel()
        steps.append("Clicked Cancel")
        cat.wait_for_view_page()
        expect(cat.frame.locator("h1")).to_contain_text(original_name)

    def test_the_payment_priority_rows_are_pre_populated_in_edit_mode(self, edit_form, steps):
        """TC-LT-055 — Payment priority rows are pre-populated in edit mode."""
        cat, _ = edit_form
        steps.append("Checked the Payment priority order grid row count")
        assert cat.get_payment_priority_row_count() >= 1

    def test_the_save_button_is_visible_when_the_header_more_actions_overflow_is_opened(self, edit_form, steps):
        """TC-LT-056 — Save button (nested under header More actions) is visible when opened."""
        cat, _ = edit_form
        steps.append("Opened the header 'More actions' overflow")
        cat._open_header_more_actions()
        expect(cat.frame.get_by_role("button", name="Save")).to_be_visible()
        cat.page.keyboard.press("Escape")

    def test_saving_an_updated_loan_type_name_persists_the_change_on_the_view_page(self, edit_form, unique_loan_type_name, steps):
        """[new] Save persists an updated Loan type name; the View page reflects it."""
        cat, _ = edit_form
        new_name = unique_loan_type_name + "_ED"
        steps.append(f"Changed Loan type name to '{new_name}'")
        cat.fill_name(new_name)
        cat.save()
        steps.append("Clicked Save")
        cat.wait_for_view_page()
        expect(cat.frame.locator("h1")).to_contain_text(new_name)
        # Rename back so the created_loan_type fixture's teardown can still find/delete it
        # by its original unique name.
        cat.click_edit()
        cat.fill_name(unique_loan_type_name)
        cat.save()
        cat.wait_for_view_page()

    def test_the_edit_page_title_is_user_friendly_and_does_not_expose_the_internal_object_path(self, edit_form, steps):
        """TC-LT-085 [new; KNOWN DEFECT] — The Edit page title is documented
        to read "Edit loan type: [ID]--[loan type name]" (checklist row 164),
        but live testing found it exposes the internal object path instead
        (e.g. "Edit loan-management/loan-type: 4--LT NonRev Simple 365").
        This test asserts the documented/expected friendly title and is
        expected to fail until that defect is fixed — see Jira Bug #40 in
        the Loan Type findings."""
        cat, name = edit_form
        title = cat.get_page_title()
        steps.append(f"Read the Edit page title: '{title}'")
        assert title.lower().startswith("edit loan type:"), (
            f"Expected a friendly 'Edit loan type: ...' title, got '{title}' "
            f"(known defect: exposes internal path 'loan-management/loan-type' "
            f"instead — Bug #40)"
        )
        assert "loan-management/loan-type" not in title, (
            f"Edit title should not expose the internal object path; got '{title}'"
        )

    def test_the_status_dropdown_offers_active_and_inactive_options(self, edit_form, steps):
        """TC-LT-086 [new] — Status dropdown offers 'Active' and 'Inactive'
        (checklist row 189)."""
        cat, _ = edit_form
        steps.append("Opened the Status dropdown")
        combo = cat.frame.get_by_role("combobox", name="Status").first
        combo.click()
        cat.page.wait_for_timeout(400)
        expect(cat.frame.get_by_role("option", name="Active", exact=True)).to_be_visible()
        expect(cat.frame.get_by_role("option", name="Inactive", exact=True)).to_be_visible()
        cat.page.keyboard.press("Escape")

    def test_the_interest_type_mandatory_marker_on_edit_matches_the_marker_on_create(self, edit_form, steps):
        """TC-LT-087 [new] — Fields marked mandatory on Create must carry the
        same mandatory (red asterisk) marker on Edit when they remain
        editable there (checklist row 217 / E1). 'Interest type' is
        mandatory and editable on both pages, so its marker should match."""
        cat, _ = edit_form
        steps.append("Checked whether 'Interest type' carries the mandatory asterisk on Edit")
        assert cat.is_field_mandatory("Interest type"), (
            "'Interest type' is mandatory on Create and remains editable on Edit; "
            "it should carry the same red-asterisk marker here"
        )

    def test_the_interest_calculation_method_mandatory_marker_on_edit_matches_the_marker_on_create(
        self, edit_form, steps
    ):
        """TC-LT-088 [new] — 'Interest calculation method' is mandatory and
        editable on both Create and Edit, so its mandatory marker should
        match on both (checklist row 217)."""
        cat, _ = edit_form
        steps.append("Checked whether 'Interest calculation method' carries the mandatory asterisk on Edit")
        assert cat.is_field_mandatory("Interest calculation method"), (
            "'Interest calculation method' is mandatory on Create and remains "
            "editable on Edit; it should carry the same red-asterisk marker here"
        )

    def test_the_edit_page_loads_type_interest_calculation_method_and_status_fully_populated(self, edit_form, steps):
        """TC-LT-089 [new] — Edit page always loads the record fully: Type
        value, Interest calculation method and Status are all populated, not
        left blank/'--' (checklist row 218 / E2)."""
        cat, _ = edit_form
        steps.append("Checked Type, Interest calculation method and Status are all populated")
        expect(cat.frame.get_by_text("Revolving", exact=True).first).to_be_visible()
        combo = cat.frame.get_by_role("combobox", name="Interest calculation method").first
        expect(combo).not_to_contain_text("--")
        status_combo = cat.frame.get_by_role("combobox", name="Status").first
        expect(status_combo).not_to_contain_text("--")

    def test_editing_a_revolving_loan_type_requires_keeping_at_least_one_interest_row(
        self, created_loan_type, loan_type_listing_page, steps
    ):
        """TC-LT-090 [new] — On Edit, a Revolving Loan Type must retain at
        least one Interest row in Payment priority order; removing it and
        saving is rejected (checklist row 207)."""
        listing: LoanTypeListingPage = loan_type_listing_page
        name = created_loan_type
        listing.navigate_to_list()
        listing.search_by_name(name)
        listing.open_record_by_name(name)
        cat = LoanTypePage(listing.page)
        cat.click_edit()
        steps.append(f"Opened Edit form for Revolving '{name}' (fixture creates one Interest row)")

        row_count = cat.get_payment_priority_row_count()
        assert row_count >= 1, "Fixture record should have at least one Payment priority row"
        cat.click_remove_row(0)
        steps.append("Removed the only Payment priority row (the Interest row)")
        cat.save()
        steps.append("Clicked Save with zero Payment priority rows on a Revolving loan type")
        expect(cat.frame.get_by_role("alert")).to_be_visible()

    def test_editing_a_non_revolving_loan_type_requires_keeping_both_a_principal_row_and_an_interest_row(
        self, loan_type_listing_page, unique_loan_type_name, steps
    ):
        """TC-LT-091 [new] — On Edit, a Non-revolving Loan Type must retain
        both a Principal row AND an Interest row; leaving only one is
        rejected on Save (checklist row 208)."""
        from pages.loan_type.type_page import LoanTypePage as _LTP

        listing: LoanTypeListingPage = loan_type_listing_page
        listing.click_create()
        lt = _LTP(listing.page)
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Non-revolving")
        lt.set_interest_type("Simple")
        lt.set_interest_calculation_method("30/360")
        lt.set_order_entry_transaction_definition(
            "loan", "Loan management invoicing"
        )
        lt.set_item_for_principal_posting("loan", "p01--Loan principal item")
        lt.set_item_for_interest_posting("interest", "i01--Loan interest item")
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Interest")
        lt.click_add_row()
        lt.set_row_sort_order("2", 1)
        lt.set_row_type("Principal", 1)
        lt.save()
        lt.wait_for_view_page()
        steps.append(f"Created Non-revolving '{unique_loan_type_name}' with Principal + Interest rows")

        try:
            lt.click_edit()
            steps.append("Opened Edit form")
            lt.click_remove_row(1)
            steps.append("Removed the Principal row, leaving only Interest")
            lt.save()
            steps.append("Clicked Save with only an Interest row on a Non-revolving loan type")
            expect(lt.frame.get_by_role("alert")).to_contain_text(
                "principal and interest"
            )
        finally:
            # Cleanup — navigate back to a known-good state and delete.
            listing.navigate_to_list()
            listing.search_by_name(unique_loan_type_name)
            if listing.is_record_visible(unique_loan_type_name):
                listing.open_record_by_name(unique_loan_type_name)
                lt.click_delete()
                lt.confirm_delete_in_modal()

    def test_navigating_away_via_the_back_arrow_without_saving_discards_unsaved_changes(
        self, edit_form, steps
    ):
        """TC-LT-092 [new] — Navigating away via the back arrow without
        saving discards all unsaved changes (checklist row 210)."""
        cat, original_name = edit_form
        steps.append("Changed the Loan type name without saving")
        cat.fill_name("UNSAVED_CHANGE_SHOULD_NOT_PERSIST")
        cat.frame.get_by_role("button", name="Back to previous page").first.click()
        steps.append("Clicked the back arrow instead of Save")
        cat.wait_for_view_page()
        expect(cat.frame.locator("h1")).to_contain_text(original_name)
        expect(
            cat.frame.get_by_text("UNSAVED_CHANGE_SHOULD_NOT_PERSIST")
        ).to_have_count(0)
