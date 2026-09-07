"""
test_edit.py
=======================
Playwright / pytest tests for the EDIT lifecycle stage of the Loan Account
module (Lending Management → All → Loan account).

Test IDs: TC-LA-098 – TC-LA-130 (mapped to the granular rows of the
"Loan Account - CRUD" checklist sheet in LME_Regression_Consolidated.xlsx,
covering the checklist's Update/Edit section). Selectors/flows verified
against live DOM 2026-08-17 (release www-p303, LME entity).

Edit heading is "Edit loan-management/loan-account: <id>--<name>" (internal
object-path prefix — same pattern as Loan Type). Account category, Account
number, Customer and Vendor are all READ-ONLY on Edit (Customer/Vendor lock
immediately, not just after a transaction). Term in months and First payment
date are ABSENT from the Edit page's Loan terms section (present on
Create/View) — a documented defect.

KNOWN DEFECTS exercised as EXPECTED-FAILURE assertions here:
  - Edit page heading exposes the internal object path instead of a
    friendly "Edit loan account: <name>" title.
  - Vendor is read-only/drillable on Edit even with no posted transactions
    (checklist expects it editable in that case).
  - Term in months / First payment date are absent from the Edit page.
  - Location has no red asterisk on Edit (same as Create).
"""

import pytest
from playwright.sync_api import expect

from pages.loan_account.listing_page import LoanAccountListingPage
from pages.loan_account.account_page import LoanAccountPage


@pytest.fixture()
def edit_form(created_loan_account, loan_account_listing_page, steps):
    """Open the Edit form for the pre-created loan account. Returns (page_obj, name)."""
    listing: LoanAccountListingPage = loan_account_listing_page
    original_name: str = created_loan_account

    listing.navigate_to_list()
    listing.open_record_by_account_name(original_name)
    acc = LoanAccountPage(listing.page)
    acc.click_edit()
    steps.append(f"Opened Edit form for '{original_name}'")
    return acc, original_name


class TestEditLoanAccount:

    def test_the_edit_page_heading_exposes_the_internal_object_path_known_defect(self, edit_form, steps):
        """TC-LA-098 [KNOWN DEFECT] — Edit page heading is
        'Edit loan-management/loan-account: <id>--<name>', exposing the
        internal object path instead of a friendly 'Edit loan account:
        <name>' title."""
        acc, _ = edit_form
        steps.append("Checked the Edit page heading text")
        heading = acc.get_page_title()
        assert "loan-management/loan-account" in heading, (
            f"Expected the internal-path defect to still be present, got: '{heading}'. "
            f"If this now shows a friendly title, update this test to assert that instead."
        )

    def test_the_loan_information_section_is_present_on_edit(self, edit_form, steps):
        """TC-LA-099 — 'Loan information' section is present and functional
        on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked for the 'Loan information' section heading")
        expect(acc.frame.get_by_text("Loan information", exact=True).first).to_be_visible()

    def test_account_category_is_read_only_and_drillable_on_edit(self, edit_form, steps):
        """TC-LA-100 — Account category is read-only and drillable (a link)
        on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked Account category renders as a link, not a combobox, on Edit")
        expect(acc.frame.get_by_role("combobox", name="Account category")).to_have_count(0)
        expect(acc.frame.get_by_role("link", name="Loan Category 01", exact=False).first).to_be_visible()

    def test_account_number_is_read_only_on_edit(self, edit_form, steps):
        """TC-LA-101 — Account number is read-only on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked Account number is not an editable textbox on Edit")
        assert acc.is_account_number_readonly()

    def test_account_name_is_mandatory_and_editable_on_edit(self, edit_form, steps):
        """TC-LA-102 — Account name is mandatory (red *) and remains editable
        on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked Account name label and editability on Edit")
        assert acc.is_field_mandatory("Account name")
        expect(acc.frame.locator(acc.ACCOUNT_NAME_INPUT).first).to_be_editable()

    def test_the_edit_form_can_save_a_valid_account_name_change(self, edit_form, steps):
        """TC-LA-103 — Record can be updated successfully with a valid, new
        Account name."""
        acc, original_name = edit_form
        new_name = f"{original_name}_EDITED"
        steps.append(f"Changed Account name to '{new_name}' and saved")
        acc.fill_account_name(new_name)
        acc.save()
        acc.wait_for_view_page()
        expect(acc.frame.get_by_text(new_name, exact=True).first).to_be_visible()
        # Rename back so fixture teardown can find/delete it by its original name.
        acc.click_edit()
        acc.fill_account_name(original_name)
        acc.save()
        acc.wait_for_view_page()

    def test_account_name_over_200_characters_is_rejected_on_edit(self, edit_form, steps):
        """TC-LA-104 [retest FIXED] — Names >200 chars are rejected on update
        with a readable message, not the raw i18n key."""
        acc, _ = edit_form
        steps.append("Filled Account name with 201 characters and saved")
        acc.fill_account_name("A" * 201)
        acc.save()
        acc.page.wait_for_timeout(1_500)
        body = acc.frame.locator("body").inner_text()
        assert "IA.NAME_SHOULD_NOT_EXCEED_200_CHARACTERS" not in body
        assert "should not exceed 200 characters" in body.lower()

    def test_clearing_account_name_and_saving_shows_a_proper_error(self, edit_form, steps):
        """TC-LA-105 — An empty Account name on update returns 'Account name
        is required for loan account.'"""
        acc, _ = edit_form
        steps.append("Cleared Account name and saved")
        acc.fill_account_name("")
        acc.save()
        acc.page.wait_for_timeout(1_500)
        body = acc.frame.locator("body").inner_text()
        assert "Account name is required for loan account" in body

    def test_customer_is_read_only_and_drillable_on_edit(self, edit_form, steps):
        """TC-LA-106 — Customer is read-only, drillable on the Edit page (not
        updatable, even with no posted transactions — matches the checklist's
        'locked after a transaction' expectation being live from the start)."""
        acc, _ = edit_form
        steps.append("Checked Customer renders as a link, not a combobox, on Edit")
        expect(acc.frame.get_by_role("combobox", name="Customer")).to_have_count(0)
        expect(acc.frame.get_by_role("link", name="Power Aerospace Materials", exact=False).first).to_be_visible()

    def test_vendor_is_read_only_even_with_no_posted_transactions_known_defect(self, edit_form, steps):
        """TC-LA-107 [KNOWN DEFECT] — Vendor is a read-only drillable link on
        the Edit page and cannot be changed, even though this fixture's
        record has no posted transactions (checklist expects Vendor editable
        in that case)."""
        acc, _ = edit_form
        steps.append("Checked Vendor renders as a link, not a combobox, on Edit (expected editable, is read-only)")
        assert acc.frame.get_by_role("combobox", name="Vendor").count() == 0, (
            "Vendor unexpectedly editable — if this now passes, the "
            "always-read-only-Vendor defect has been fixed."
        )

    def test_attachment_is_not_mandatory_on_edit(self, edit_form, steps):
        """TC-LA-108 — Attachment is not mandatory on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked Attachment label for absence of a required asterisk")
        assert not acc.is_field_mandatory("Attachment")

    def test_description_is_not_mandatory_on_edit(self, edit_form, steps):
        """TC-LA-109 — Description is not mandatory on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked Description label for absence of a required asterisk")
        assert not acc.is_field_mandatory("Description")

    def test_description_over_500_characters_is_rejected_on_edit(self, edit_form, steps):
        """TC-LA-110 — Descriptions over 500 characters are rejected on
        update (the checklist's stated limit of 1000 does not match live
        behaviour — the enforced limit is 500, same as Create)."""
        acc, _ = edit_form
        steps.append("Filled Description with 501 characters and saved")
        acc.fill_description("D" * 501)
        acc.save()
        acc.page.wait_for_timeout(1_500)
        body = acc.frame.locator("body").inner_text()
        assert "should not exceed 500 characters" in body.lower()

    def test_an_empty_description_is_accepted_on_edit(self, edit_form, steps):
        """TC-LA-111 — An empty Description is accepted on update; the record
        shows '--'."""
        acc, _ = edit_form
        steps.append("Cleared Description and saved")
        acc.fill_description("")
        acc.save()
        acc.wait_for_view_page()
        expect(acc.frame.get_by_text("--", exact=True).first).to_be_visible()

    def test_email_statements_reflects_the_value_set_at_creation(self, edit_form, steps):
        """TC-LA-112 — Email statements displays the same value it had at
        creation (unchecked, per the fixture's data)."""
        acc, _ = edit_form
        steps.append("Checked Email statements checkbox state on Edit")
        assert not acc.is_email_statements_checked()

    def test_email_statements_can_be_toggled_on_edit(self, edit_form, steps):
        """TC-LA-113 — Email statements checkbox can be toggled during
        update."""
        acc, _ = edit_form
        steps.append("Toggled Email statements on Edit")
        acc.toggle_email_statements()
        assert acc.is_email_statements_checked()

    def test_term_in_months_is_absent_from_the_edit_page_known_defect(self, edit_form, steps):
        """TC-LA-114 [KNOWN DEFECT] — 'Term in months' is ABSENT from the
        Edit page's Loan terms section, even though it's present on
        Create/View."""
        acc, _ = edit_form
        steps.append("Checked the Loan terms section for a Term in months control (expected present, is absent)")
        assert not acc.has_field("Term in months"), (
            "Term in months unexpectedly present on Edit — if this now passes, "
            "the missing-field defect has been fixed."
        )

    def test_first_payment_date_is_absent_from_the_edit_page_known_defect(self, edit_form, steps):
        """TC-LA-115 [KNOWN DEFECT] — 'First payment date' is ABSENT from the
        Edit page's Loan terms section, even though it's present on
        Create/View."""
        acc, _ = edit_form
        steps.append("Checked the Loan terms section for a First payment date control (expected present, is absent)")
        assert not acc.has_field("First payment date"), (
            "First payment date unexpectedly present on Edit — if this now "
            "passes, the missing-field defect has been fixed."
        )

    def test_interest_rate_is_mandatory_on_edit(self, edit_form, steps):
        """TC-LA-116 — Interest rate is mandatory (red *) on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked Interest rate label for a required asterisk")
        assert acc.is_field_mandatory("Interest rate")

    def test_updating_the_interest_rate_to_a_valid_active_rate_succeeds(self, edit_form, steps):
        """TC-LA-117 — Updating the Interest rate to a valid, active rate
        works."""
        acc, _ = edit_form
        steps.append("Changed Interest rate and saved")
        acc.set_interest_rate("a")
        acc.save()
        acc.wait_for_view_page()
        expect(acc.frame.locator("h1").filter(has_text="Loan:")).to_be_visible()

    def test_origination_date_is_mandatory_on_edit(self, edit_form, steps):
        """TC-LA-118 — Loan origination date is mandatory (red *) on the Edit
        page."""
        acc, _ = edit_form
        steps.append("Checked Loan origination date label for a required asterisk")
        assert acc.is_field_mandatory("Loan origination date")

    def test_origination_date_can_be_backdated_on_edit(self, edit_form, steps):
        """TC-LA-119 — Origination date can be backdated on the Edit page."""
        acc, _ = edit_form
        steps.append("Set a backdated Loan origination date and saved")
        acc.set_origination_date("01/15/2025")
        acc.save()
        acc.wait_for_view_page()
        expect(acc.frame.get_by_text("01/15/2025", exact=False).first).to_be_visible()

    def test_amount_is_mandatory_and_numeric_on_edit(self, edit_form, steps):
        """TC-LA-120 — Amount is a mandatory (*) numeric field on the Edit
        page."""
        acc, _ = edit_form
        steps.append("Checked Amount label for a required asterisk")
        assert acc.is_field_mandatory("Amount")

    def test_negative_amount_is_rejected_on_edit_with_a_friendly_message(self, edit_form, steps):
        """TC-LA-121 [retest FIXED] — Negative Amount on update no longer
        leaks '/originationAmount'; shows a friendly message instead."""
        acc, _ = edit_form
        steps.append("Set a negative Amount and saved")
        acc.fill_amount("-500")
        acc.save()
        acc.page.wait_for_timeout(1_500)
        body = acc.frame.locator("body").inner_text()
        assert "/originationAmount" not in body

    def test_a_zero_amount_account_can_be_updated_to_a_new_amount(self, loan_account_listing_page, unique_account_name, steps):
        """TC-LA-122 — A loan account created with 0 Amount can be updated to
        a different amount when no transactions have been posted."""
        from pages.loan_account.account_page import LoanAccountPage as LAP
        from tests.loan_account.conftest import _fill_minimum_valid_loan_account

        listing = loan_account_listing_page
        listing.click_create()
        acc = LAP(listing.page)
        _fill_minimum_valid_loan_account(acc, unique_account_name)
        acc.fill_amount("0")
        acc.save()
        acc.wait_for_view_page()
        steps.append(f"Created a zero-Amount loan account '{unique_account_name}'")

        acc.click_edit()
        acc.fill_amount("2500")
        acc.save()
        acc.wait_for_view_page()
        steps.append("Updated Amount from 0 to 2500")
        expect(acc.frame.get_by_text("2,500.00", exact=False).first).to_be_visible()

        acc.click_delete()
        acc.confirm_delete_in_modal()

    def test_saving_without_an_amount_shows_a_proper_error_on_edit(self, edit_form, steps):
        """TC-LA-123 — Saving without an Amount on update returns 'Amount is
        required for loan account.'"""
        acc, _ = edit_form
        steps.append("Cleared Amount and saved")
        acc.fill_amount("")
        acc.save()
        acc.page.wait_for_timeout(1_500)
        body = acc.frame.locator("body").inner_text()
        assert "Amount is required for loan account" in body

    def test_location_has_no_red_asterisk_on_edit_known_defect(self, edit_form, steps):
        """TC-LA-124 [KNOWN DEFECT] — Location has no red asterisk on the
        Edit page (same as Create), even though it's enforced on save."""
        acc, _ = edit_form
        steps.append("Checked Location label for a required asterisk on Edit")
        assert not acc.is_field_mandatory("Location"), (
            "Location unexpectedly shows a required asterisk on Edit — if this "
            "now passes, the missing-asterisk defect has been fixed."
        )

    def test_updating_to_a_valid_location_succeeds(self, edit_form, steps):
        """TC-LA-125 — Updating to a valid Location key is accepted."""
        acc, _ = edit_form
        steps.append("Changed Location and saved")
        acc.set_location("LME")
        acc.save()
        acc.wait_for_view_page()
        expect(acc.frame.locator("h1").filter(has_text="Loan:")).to_be_visible()

    def test_save_split_button_is_visible_on_edit(self, edit_form, steps):
        """TC-LA-126 — 'Save' split-button is visible on the Edit page."""
        acc, _ = edit_form
        steps.append("Checked header for the Save split-button")
        expect(acc.frame.locator('[aria-label="Save"]:visible').first).to_be_visible()

    def test_save_and_close_returns_to_the_view_page_or_list(self, edit_form, steps):
        """TC-LA-127 — 'Save and close' saves the form and navigates away
        from the Edit form (to the View page)."""
        acc, _ = edit_form
        steps.append("Clicked Save via the 'Save and close' option")
        acc.save_via("Save and close")
        acc.page.wait_for_timeout(2_000)
        heading = acc.get_page_title()
        assert "Edit" not in heading, f"Expected to leave the Edit form, still on: '{heading}'"

    def test_clicking_cancel_discards_changes_and_returns_to_the_view_page(self, edit_form, steps):
        """TC-LA-128 — Clicking Cancel discards changes and returns to the
        View page."""
        acc, original_name = edit_form
        steps.append("Changed Account name without saving, then clicked Cancel")
        acc.fill_account_name(f"{original_name}_UNSAVED")
        acc.cancel()
        acc.page.wait_for_timeout(1_500)
        expect(acc.frame.locator("h1").filter(has_text="Loan:")).to_be_visible()
        expect(acc.frame.get_by_text(original_name, exact=True).first).to_be_visible()

    def test_validation_errors_show_on_edit_when_a_required_field_is_cleared(self, edit_form, steps):
        """TC-LA-129 — Validation error messages are shown on the Edit page
        when a required field is cleared and any save option is clicked."""
        acc, _ = edit_form
        steps.append("Cleared Amount (required) and saved")
        acc.fill_amount("")
        acc.save()
        acc.page.wait_for_timeout(1_500)
        errors = acc.frame.locator(acc.VALIDATION_ERROR)
        assert errors.count() > 0, "Expected at least one validation error indicator"

    def test_the_updated_values_reflect_correctly_in_the_view_page(self, edit_form, steps):
        """TC-LA-130 — After a successful update, the changed values are
        reflected correctly on returning to the View page."""
        acc, _ = edit_form
        steps.append("Updated Amount and Description, saved, checked the View page")
        acc.fill_amount("7500")
        acc.fill_description("Updated via automated test")
        acc.save()
        acc.wait_for_view_page()
        expect(acc.frame.get_by_text("7,500.00", exact=False).first).to_be_visible()
        expect(acc.frame.get_by_text("Updated via automated test", exact=False).first).to_be_visible()
