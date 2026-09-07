"""
test_create.py
=========================
Playwright / pytest tests for the CREATE lifecycle stage of the Loan
Interest Rate module (Lending Management → Setup → Loan interest rates).

Test IDs: TC-LIR-011 – TC-LIR-024
Selectors/flows verified against live DOM 2026-07-16. See
TEST_CASES_Loan_Interest_Rate.md for the full field/behaviour inventory,
including two server-side validations not documented anywhere in the UI:
at least one schedule row is required, and a row's Start date must be the
first day of a month.
"""

import datetime

import pytest
from playwright.sync_api import expect

from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
from pages.loan_interest_rate.rate_page import LoanInterestRatePage


def _first_of_next_month() -> str:
    today = datetime.date.today()
    year = today.year + (1 if today.month == 12 else 0)
    month = 1 if today.month == 12 else today.month + 1
    return f"{month:02d}/01/{year}"


def _fifteenth_of_this_month() -> str:
    today = datetime.date.today()
    return f"{today.month:02d}/15/{today.year}"


@pytest.fixture()
def create_form(loan_interest_rate_listing_page, steps):
    """Open the Create form and return a ready-to-use page object."""
    listing: LoanInterestRateListingPage = loan_interest_rate_listing_page
    listing.click_create()
    steps.append("Opened the Loan interest rate Create form")
    return LoanInterestRatePage(listing.page)


class TestCreateLoanInterestRate:

    def test_verify_that_the_name_field_is_present_on_the_create_form(self, create_form, steps):
        """TC-LIR-011 — Create form has a Name text field."""
        steps.append("Checked for the 'Name' textbox")
        expect(create_form.frame.locator(create_form.NAME_INPUT).first).to_be_visible()

    def test_verify_that_saving_with_an_empty_name_is_blocked(self, create_form, steps):
        """TC-LIR-012 — Name is required; saving without it keeps the user on Create."""
        steps.append("Left Name empty and clicked Save")
        create_form.save()
        create_form.page.wait_for_timeout(1_500)
        steps.append("Verified we're still on the Create form")
        expect(
            create_form.frame.get_by_role("heading", name="Create loan interest rate")
        ).to_be_visible()

    def test_verify_that_revolving_and_non_revolving_type_options_are_visible(self, create_form, steps):
        """TC-LIR-013 — Type field shows Revolving/Non-revolving options."""
        steps.append("Checked the Type radio group")
        expect(create_form.frame.get_by_role("radio", name="Revolving", exact=True)).to_be_visible()
        expect(create_form.frame.get_by_role("radio", name="Non-revolving", exact=True)).to_be_visible()

    def test_verify_that_the_add_row_button_is_present_in_the_schedule_section(self, create_form, steps):
        """TC-LIR-014 — 'Add row' button is present in the schedule section."""
        steps.append("Scrolled to the Loan interest rate schedule section")
        expect(create_form.frame.get_by_role("button", name="Add row").first).to_be_visible()

    def test_verify_that_the_schedule_grid_displays_all_expected_columns(self, create_form, steps):
        """TC-LIR-015 — Schedule grid has Start date, Interest rate (%), Notes, Attachment columns."""
        steps.append("Checked schedule grid column headers")
        headers = create_form.frame.get_by_role("columnheader")
        text = " ".join(h.inner_text() for h in headers.all()).lower()
        assert "start date" in text
        assert "interest rate" in text
        assert "notes" in text
        assert "attachment" in text

    def test_verify_that_the_start_date_column_is_marked_as_required(self, create_form, steps):
        """TC-LIR-016 — Start date column header is marked required ('*')."""
        steps.append("Checked the Start date column header for a required asterisk")
        header = create_form.frame.get_by_role("columnheader", name="Start date").first
        expect(header.get_by_text("*", exact=True)).to_be_visible()

    def test_verify_that_the_interest_rate_column_is_marked_as_required(self, create_form, steps):
        """TC-LIR-017 — Interest rate (%) column header is marked required ('*')."""
        steps.append("Checked the Interest rate (%) column header for a required asterisk")
        header = create_form.frame.get_by_role("columnheader", name="Interest rate").first
        expect(header.get_by_text("*", exact=True)).to_be_visible()

    def test_verify_that_clicking_add_row_increases_the_schedule_row_count(self, create_form, steps):
        """TC-LIR-018 — Clicking 'Add row' increments the schedule grid by one row."""
        before = create_form.get_schedule_row_count()
        steps.append(f"Recorded starting row count = {before}")
        create_form.click_add_row()
        after = create_form.get_schedule_row_count()
        steps.append(f"Row count after Add row = {after}")
        assert after == before + 1

    def test_verify_that_clicking_remove_row_decreases_the_schedule_row_count(self, create_form, steps):
        """TC-LIR-019 — Clicking Remove row decrements the schedule grid."""
        create_form.click_add_row()
        before = create_form.get_schedule_row_count()
        steps.append(f"Added a row; row count = {before}")
        create_form.click_remove_row(0)
        after = create_form.get_schedule_row_count()
        steps.append(f"Row count after Remove row = {after}")
        assert after == before - 1

    def test_verify_that_at_least_one_schedule_row_is_required(self, create_form, unique_loan_interest_rate_name, steps):
        """TC-LIR-020 [undocumented] — Saving with zero schedule rows shows a validation error."""
        rp = create_form
        rp.fill_name(unique_loan_interest_rate_name)
        rp.select_type("Revolving")
        steps.append("Filled Name and Type but left the schedule grid empty")
        rp.save()
        steps.append("Clicked Save with zero schedule rows")
        expect(rp.frame.get_by_role("alert")).to_contain_text(
            "At-least one rate entry is required for a Loan Interest Rate"
        )

    def test_verify_that_a_schedule_start_date_must_be_the_first_day_of_a_month(self, create_form, unique_loan_interest_rate_name, steps):
        """TC-LIR-021 [undocumented] — A Start date that isn't the 1st of a month is rejected."""
        rp = create_form
        rp.fill_name(unique_loan_interest_rate_name)
        rp.select_type("Revolving")
        rp.click_add_row()
        rp.set_row_start_date(_fifteenth_of_this_month())
        rp.set_row_interest_rate("4.0")
        steps.append(f"Added a schedule row with Start date = {_fifteenth_of_this_month()} (mid-month)")
        rp.save()
        steps.append("Clicked Save with a non-1st-of-month Start date")
        expect(rp.frame.get_by_role("alert")).to_contain_text(
            "Interest rate entries can be only effective from the first date of the month"
        )

    def test_verify_that_the_save_button_is_visible_on_the_create_form(self, create_form, steps):
        """TC-LIR-022 — Save button is visible on the create form."""
        steps.append("Checked header for Save action")
        expect(create_form.frame.locator('[role="menuitem"]:has-text("Save")')).to_be_visible()

    def test_verify_that_cancel_discards_changes_and_returns_to_the_list(self, create_form, unique_loan_interest_rate_name, steps):
        """TC-LIR-023 — Cancel discards changes and returns to the Loan interest rates list."""
        create_form.fill_name(unique_loan_interest_rate_name)
        steps.append(f"Filled Name = '{unique_loan_interest_rate_name}'")
        create_form.cancel()
        steps.append("Clicked Cancel")
        expect(
            create_form.frame.get_by_role("heading", name="Loan interest rates")
        ).to_be_visible()

    def test_verify_that_a_valid_interest_rate_saves_and_opens_the_view_page(self, create_form, unique_loan_interest_rate_name, steps):
        """TC-LIR-024 — A fully valid Loan Interest Rate (Name + Type + one 1st-of-month row) saves."""
        rp = create_form
        rp.fill_name(unique_loan_interest_rate_name)
        rp.select_type("Revolving")
        rp.click_add_row()
        rp.set_row_start_date(_first_of_next_month())
        rp.set_row_interest_rate("5.5")
        steps.append(f"Filled all required fields for '{unique_loan_interest_rate_name}'")
        rp.save()
        steps.append("Clicked Save")
        rp.wait_for_view_page()
        expect(rp.frame.locator("h1").filter(has_text="Loan interest rates:")).to_be_visible()
        # Cleanup
        rp.click_delete()
        rp.confirm_delete_in_modal()

    def test_verify_that_the_create_page_title_is_readable(self, create_form, steps):
        """CREATE SL 1 — The page title is Create loan interest rate."""
        steps.append("Read the Create page title")
        expect(
            create_form.frame.get_by_role("heading", name="Create loan interest rate")
        ).to_be_visible()

    def test_verify_that_both_create_sections_can_be_collapsed_and_expanded(
        self, create_form, steps
    ):
        """CREATE SL 2 — Both form sections provide working expand/collapse controls."""
        for section in (
            "Loan interest rate information",
            "Loan interest rate schedule",
        ):
            steps.append(f"Collapsed and expanded {section}")
            assert create_form.section_has_toggle(section), f"No toggle for {section}"
            create_form.collapse_named_section(section)
            assert not create_form.is_named_section_expanded(section)
            create_form.expand_named_section(section)
            assert create_form.is_named_section_expanded(section)

    def test_verify_that_the_attachment_field_is_an_optional_editable_picker(
        self, create_form, steps
    ):
        """CREATE SL 40-42 — Attachment is an optional picker and may remain blank."""
        create_form.click_add_row()
        steps.append("Activated the Attachment cell on a new schedule row")
        control = create_form.attachment_control(0)
        expect(control).to_be_visible()
        assert control.is_editable()
        attachment_header = next(
            (h for h in create_form.schedule_column_headers() if "Attachment" in h), ""
        )
        assert attachment_header and "*" not in attachment_header

    def test_verify_that_a_revolving_rate_can_be_created_with_a_backdated_start_date(
        self, interest_rate_scenario_factory, steps
    ):
        """CREATE SL 21 / VALIDATION SL 10 — A valid first-of-month date may be backdated."""
        steps.append("Created a Revolving rate with a backdated start month")
        scenario = interest_rate_scenario_factory.create_rate(dates=("07/01/2026",))
        assert scenario["dates"] == ["07/01/2026"]

    def test_verify_that_a_revolving_rate_can_be_created_with_a_future_start_date(
        self, interest_rate_scenario_factory, steps
    ):
        """CREATE SL 21 / VALIDATION SL 10 — A valid first-of-month date may be future dated."""
        steps.append("Created a Revolving rate with a future start month")
        scenario = interest_rate_scenario_factory.create_rate(dates=("01/01/2027",))
        assert scenario["dates"] == ["01/01/2027"]

    def test_verify_that_an_interest_rate_with_more_than_four_decimal_places_is_rejected(
        self, create_form, unique_loan_interest_rate_name, steps
    ):
        """CREATE SL 27 / VALIDATION SL 16 — Five decimal places are rejected."""
        rp = create_form
        rp.fill_name(unique_loan_interest_rate_name)
        rp.select_type("Revolving")
        rp.click_add_row()
        rp.set_row_start_date(_first_of_next_month())
        rp.set_row_interest_rate("5.12345")
        steps.append("Saved a rate with five decimal places")
        rp.save()
        rp.page.wait_for_timeout(2_000)
        assert "Create" in rp.get_page_title() or rp.error_banner_text()

    def test_verify_that_save_and_close_saves_the_record_and_returns_to_the_lister(
        self, create_form, unique_loan_interest_rate_name, steps
    ):
        """CREATE SL 52 — Save and close saves and returns to Loan interest rates."""
        rp = create_form
        rp.fill_name(unique_loan_interest_rate_name)
        rp.select_type("Revolving")
        rp.click_add_row()
        rp.set_row_start_date(_first_of_next_month())
        rp.set_row_interest_rate("5.25")
        steps.append("Saved the valid form using Save and close")
        try:
            rp.save_via("Save and close")
            expect(
                rp.frame.get_by_role("heading", name="Loan interest rates")
            ).to_be_visible()
        finally:
            listing = LoanInterestRateListingPage(rp.page)
            listing.navigate_to_list()
            listing.search_by_name(unique_loan_interest_rate_name)
            if listing.is_record_visible(unique_loan_interest_rate_name):
                listing.open_record_by_name(unique_loan_interest_rate_name)
                rp.click_delete()
                rp.confirm_delete_in_modal()

    def test_verify_that_save_and_close_does_not_bypass_required_field_validation(
        self, create_form, steps
    ):
        """CREATE SL 54 — Save and close obeys the same validation rules as Save."""
        steps.append("Used Save and close with all required fields empty")
        create_form.save_via("Save and close")
        create_form.page.wait_for_timeout(1_000)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_save_and_new_does_not_bypass_required_field_validation(
        self, create_form, steps
    ):
        """CREATE SL 54 — Save and new obeys the same validation rules as Save."""
        steps.append("Used Save and new with all required fields empty")
        create_form.save_via("Save and new")
        create_form.page.wait_for_timeout(1_000)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_a_non_revolving_rate_rejects_a_second_schedule_entry(
        self, create_form, unique_loan_interest_rate_name, steps
    ):
        """CREATE SL A10 — Non-revolving rates allow only one schedule entry."""
        rp = create_form
        rp.fill_name(unique_loan_interest_rate_name)
        rp.select_type("Non-revolving")
        for _ in range(2):
            rp.click_add_row()
        rp.set_row_start_date("09/01/2026", 0)
        rp.set_row_interest_rate("5", 0)
        rp.set_row_start_date("10/01/2026", 1)
        rp.set_row_interest_rate("6", 1)
        steps.append("Attempted to save two rows for a Non-revolving rate")
        rp.save()
        rp.page.wait_for_timeout(2_000)
        message = rp.error_banner_text()
        assert "Create" in rp.get_page_title() or message
        if message:
            assert "non" in message.lower() and "one" in message.lower()

    @pytest.mark.xfail(
        reason="The current release can expose raw backend details for a missing schedule rate.",
        strict=False,
    )
    def test_verify_that_required_field_errors_are_clear_and_do_not_expose_backend_details(
        self, create_form, unique_loan_interest_rate_name, steps
    ):
        """CREATE SL A8 — Required-field messages are readable and non-technical."""
        rp = create_form
        rp.fill_name(unique_loan_interest_rate_name)
        rp.select_type("Revolving")
        rp.click_add_row()
        rp.set_row_start_date(_first_of_next_month())
        steps.append("Saved with the schedule rate missing and inspected the message")
        rp.save()
        rp.page.wait_for_timeout(2_000)
        message = rp.error_banner_text()
        assert message, "No required-rate message was shown"
        lowered = message.lower()
        for technical in ("java", "exception", "/loan", "pattern", "nullpointer"):
            assert technical not in lowered, message
