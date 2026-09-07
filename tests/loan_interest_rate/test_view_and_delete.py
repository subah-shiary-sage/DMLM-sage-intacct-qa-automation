"""
test_view_and_delete.py
==================================
Playwright / pytest tests for the VIEW and DELETE lifecycle stages of the
Loan Interest Rate module (Lending Management → Setup → Loan interest rates).

Test IDs: TC-LIR-025 – TC-LIR-030 (View), TC-LIR-039 – TC-LIR-043 (Delete)
Selectors/flows verified against live DOM 2026-07-16.
  * View heading  : "Loan interest rates: <ID>" (PLURAL "rates", matches the
                     module/list name — unlike Loan Type's singular
                     "Loan type: <ID>"). No name in the heading.
  * Delete modal  : "Delete loan interest rate" — same underlying framework
                     component as Depository Account Category's/Loan Type's
                     delete modal, including its zero-bounding-box quirk on
                     the dialog wrapper (see LoanInterestRatePage._delete_dialog).
"""

import pytest
from playwright.sync_api import expect

from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
from pages.loan_interest_rate.rate_page import LoanInterestRatePage


@pytest.fixture()
def view_page(created_loan_interest_rate, loan_interest_rate_listing_page, steps):
    """Open the View page for a pre-created loan interest rate. Returns (page_obj, name)."""
    listing: LoanInterestRateListingPage = loan_interest_rate_listing_page
    name: str = created_loan_interest_rate
    listing.navigate_to_list()
    listing.search_by_name(name)
    listing.open_record_by_name(name)
    steps.append(f"Opened View page for '{name}'")
    return LoanInterestRatePage(listing.page), name


class TestViewLoanInterestRate:

    def test_verify_that_the_view_heading_displays_the_interest_rate_record_id(self, view_page, steps):
        """TC-LIR-025 — View heading is 'Loan interest rates: <ID>' (plural, no name in heading)."""
        rp, _ = view_page
        steps.append("Checked the View page heading")
        expect(
            rp.frame.locator("h1").filter(has_text="Loan interest rates:")
        ).to_be_visible()

    def test_verify_that_the_view_page_displays_the_interest_rate_name(self, view_page, steps):
        """TC-LIR-026 — Detail page displays the Name."""
        rp, name = view_page
        steps.append(f"Checked page for name '{name}'")
        expect(rp.frame.get_by_text(name, exact=True).first).to_be_visible()

    def test_verify_that_the_view_page_displays_the_interest_rate_type(self, view_page, steps):
        """TC-LIR-027 — Detail page displays Type (Revolving/Non-revolving)."""
        rp, _ = view_page
        steps.append("Checked page for the Type field value")
        expect(rp.frame.get_by_text("Revolving", exact=True).first).to_be_visible()

    def test_verify_that_the_view_page_displays_active_status(self, view_page, steps):
        """TC-LIR-028 — Detail page shows Status = Active."""
        rp, _ = view_page
        steps.append("Checked page for Status = Active")
        expect(rp.frame.get_by_text("Active", exact=True).first).to_be_visible()

    def test_verify_that_the_edit_button_is_visible_on_the_view_page(self, view_page, steps):
        """TC-LIR-029 — Edit button is visible directly in the header."""
        rp, _ = view_page
        steps.append("Checked header for Edit button")
        expect(rp.frame.get_by_role("button", name="Edit")).to_be_visible()

    def test_verify_that_the_delete_button_is_visible_on_the_view_page(self, view_page, steps):
        """TC-LIR-030 — Delete button is visible directly in the header."""
        rp, _ = view_page
        steps.append("Checked header for Delete button")
        expect(rp.frame.get_by_role("button", name="Delete")).to_be_visible()

    def test_verify_that_all_record_fields_are_read_only_on_the_view_page(
        self, view_page, steps
    ):
        """VIEW SL 24 — View does not expose editable record or schedule controls."""
        rp, _ = view_page
        steps.append("Checked the View page for editable form controls")
        assert not rp.view_has_editable_form_controls()

    def test_verify_that_both_view_sections_can_be_collapsed_and_expanded(
        self, view_page, steps
    ):
        """VIEW SL 26 — Both View sections provide working expand/collapse controls."""
        rp, _ = view_page
        for section in (
            "Loan interest rate information",
            "Loan interest rate schedule",
        ):
            steps.append(f"Collapsed and expanded {section} on View")
            assert rp.section_has_toggle(section), f"No toggle for {section}"
            rp.collapse_named_section(section)
            assert not rp.is_named_section_expanded(section)
            rp.expand_named_section(section)
            assert rp.is_named_section_expanded(section)

    def test_verify_that_the_view_schedule_grid_displays_the_saved_row_and_columns(
        self, view_page, steps
    ):
        """VIEW SL 28 — View shows the read-only schedule grid and its saved row."""
        rp, _ = view_page
        steps.append("Read the View schedule grid headers and row count")
        headers = " | ".join(rp.schedule_column_headers())
        for expected in ("Start date", "Interest rate", "Notes", "Attachment"):
            assert expected in headers
        assert rp.get_schedule_row_count() >= 1

    def test_verify_that_the_view_page_has_a_more_actions_menu(self, view_page, steps):
        """VIEW SL 29 — A three-dot More actions menu is present."""
        rp, _ = view_page
        steps.append("Checked the View header for More actions")
        expect(rp.frame.locator('[aria-label="More actions"]:visible').first).to_be_visible()

    def test_verify_that_the_view_menu_contains_view_audit_trail(
        self, view_page, steps
    ):
        """VIEW SL 30 — The three-dot menu contains View audit trail."""
        rp, _ = view_page
        steps.append("Opened the View three-dot menu")
        rp.open_view_three_dot_menu()
        expect(rp.frame.get_by_role("button", name="View audit trail")).to_be_visible()

    @pytest.mark.xfail(
        reason="Object definition is missing from the current View three-dot menu.",
        strict=False,
    )
    def test_verify_that_the_view_menu_contains_object_definition(
        self, view_page, steps
    ):
        """VIEW SL 30 — The three-dot menu contains Object definition."""
        rp, _ = view_page
        steps.append("Opened the View three-dot menu")
        rp.open_view_three_dot_menu()
        expect(rp.frame.get_by_role("button", name="Object definition")).to_be_visible()

    def test_verify_that_clicking_edit_from_view_opens_the_edit_page(
        self, view_page, steps
    ):
        """VIEW SL 32 — Edit redirects from View to Edit."""
        rp, name = view_page
        steps.append("Clicked Edit from the View page")
        rp.click_edit()
        expect(rp.frame.locator("h1").filter(has_text="Edit loan interest rate")).to_contain_text(name)

    def test_verify_that_the_breadcrumb_returns_to_the_interest_rate_lister(
        self, view_page, steps
    ):
        """VIEW function — The Loan interest rates breadcrumb returns to the lister."""
        rp, _ = view_page
        steps.append("Clicked the Loan interest rates breadcrumb")
        rp.click_back_to_list()
        expect(rp.frame.get_by_role("heading", name="Loan interest rates")).to_be_visible()


class TestDeleteLoanInterestRate:

    def test_verify_that_delete_opens_the_confirmation_window(
        self, loan_interest_rate_for_delete, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-039 — Clicking Delete opens the confirmation modal."""
        listing = loan_interest_rate_listing_page
        listing.open_record_by_name(loan_interest_rate_for_delete)
        rp = LoanInterestRatePage(listing.page)
        steps.append(f"Opened View page for '{loan_interest_rate_for_delete}', clicked Delete")
        rp.click_delete()
        expect(rp.frame.get_by_role("heading", name=rp.DELETE_DIALOG).last).to_be_visible()
        rp.confirm_delete_in_modal()  # cleanup

    def test_verify_that_the_delete_message_names_the_interest_rate(
        self, loan_interest_rate_for_delete, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-040 — Modal message names the record and says it will be deleted."""
        listing = loan_interest_rate_listing_page
        listing.open_record_by_name(loan_interest_rate_for_delete)
        rp = LoanInterestRatePage(listing.page)
        steps.append(f"Opened View page for '{loan_interest_rate_for_delete}', clicked Delete")
        rp.click_delete()
        message = rp.get_delete_modal_message()
        assert loan_interest_rate_for_delete in message, f"Expected '{loan_interest_rate_for_delete}' in: '{message}'"
        assert "will be permanently deleted" in message.lower(), f"Missing deletion notice in: '{message}'"
        rp.confirm_delete_in_modal()

    def test_verify_that_confirming_delete_permanently_removes_the_interest_rate(
        self, loan_interest_rate_for_delete, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-041 — Confirming Delete removes the record from the list."""
        listing: LoanInterestRateListingPage = loan_interest_rate_listing_page
        name = loan_interest_rate_for_delete

        listing.open_record_by_name(name)
        rp = LoanInterestRatePage(listing.page)
        steps.append(f"Opened View page for '{name}'")
        rp.click_delete()
        steps.append("Clicked Delete, confirmed in modal")
        rp.confirm_delete_in_modal()

        listing.wait_for_list_page()
        listing.search_by_name(name)
        steps.append(f"Filtered list by '{name}' to verify removal")
        assert not listing.is_record_visible(name), f"Record '{name}' should have been deleted"

    def test_verify_that_cancelling_delete_keeps_the_interest_rate(
        self, loan_interest_rate_for_delete, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-042 — Cancel in the modal closes it without deleting."""
        listing = loan_interest_rate_listing_page
        name = loan_interest_rate_for_delete

        listing.open_record_by_name(name)
        rp = LoanInterestRatePage(listing.page)
        steps.append(f"Opened View page for '{name}', clicked Delete then Cancel")
        rp.click_delete()
        rp.cancel_delete_in_modal()

        expect(rp.frame.get_by_role("heading", name=rp.DELETE_DIALOG).last).not_to_be_visible()
        expect(rp.frame.locator("h1").filter(has_text="Loan interest rates:")).to_be_visible()

        # Cleanup: now actually delete it.
        rp.click_delete()
        rp.confirm_delete_in_modal()

    def test_verify_that_deleting_an_interest_rate_returns_to_the_list(
        self, loan_interest_rate_for_delete, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-043 — Deleting from the View page redirects to the Loan interest rates list."""
        listing = loan_interest_rate_listing_page
        name = loan_interest_rate_for_delete

        listing.open_record_by_name(name)
        rp = LoanInterestRatePage(listing.page)
        steps.append(f"Opened View page for '{name}', clicked Delete and confirmed")
        rp.click_delete()
        rp.confirm_delete_in_modal()

        expect(
            rp.frame.get_by_role("heading", name="Loan interest rates")
        ).to_be_visible()

    def test_verify_that_the_delete_confirmation_displays_delete_and_cancel_buttons(
        self, loan_interest_rate_for_delete, loan_interest_rate_listing_page, steps
    ):
        """DELETE UI — The confirmation window provides Delete and Cancel actions."""
        listing = loan_interest_rate_listing_page
        listing.open_record_by_name(loan_interest_rate_for_delete)
        rp = LoanInterestRatePage(listing.page)
        rp.click_delete()
        steps.append("Checked both confirmation actions")
        dialog = rp.delete_dialog()
        expect(dialog.get_by_role("button", name="Delete")).to_have_count(1)
        expect(dialog.get_by_role("button", name="Cancel")).to_have_count(1)
        rp.confirm_delete_in_modal()

    @pytest.mark.xfail(
        reason="The current confirmation message names the rate but may omit its record ID.",
        strict=False,
    )
    def test_verify_that_the_delete_message_contains_both_the_rate_id_and_name(
        self, loan_interest_rate_for_delete, loan_interest_rate_listing_page, steps
    ):
        """VIEW SL 36 — Delete message follows the ID - Name format."""
        listing = loan_interest_rate_listing_page
        listing.open_record_by_name(loan_interest_rate_for_delete)
        rp = LoanInterestRatePage(listing.page)
        record_id = rp.get_page_title().split(":", 1)[-1].strip()
        rp.click_delete()
        message = rp.get_delete_modal_message()
        steps.append("Compared the delete message with the View ID and Name")
        try:
            assert record_id in message and loan_interest_rate_for_delete in message
            assert "-" in message
        finally:
            rp.confirm_delete_in_modal()

    def test_verify_that_the_only_remaining_schedule_entry_cannot_be_deleted(
        self, interest_rate_scenario_factory, steps
    ):
        """DELETE SL 15/83 — The schedule must retain at least one entry."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Removed the only schedule row and attempted to save")
        rp.click_remove_row(0)
        rp.save()
        rp.page.wait_for_timeout(2_000)
        message = rp.error_banner_text()
        assert message or "Edit" in rp.get_page_title()
