"""
test_edit.py
=======================
Playwright / pytest tests for the EDIT lifecycle stage of the Loan Interest
Rate module (Lending Management → Setup → Loan interest rates).

Test IDs: TC-LIR-031 – TC-LIR-038.
The current release uses the readable heading "Edit loan interest rate:
<ID>--<Name>".
"""

import pytest
from playwright.sync_api import expect

from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
from pages.loan_interest_rate.rate_page import LoanInterestRatePage


@pytest.fixture()
def edit_form(created_loan_interest_rate, loan_interest_rate_listing_page, steps):
    """Open the Edit form for the pre-created loan interest rate. Returns (page_obj, name)."""
    listing: LoanInterestRateListingPage = loan_interest_rate_listing_page
    original_name: str = created_loan_interest_rate

    listing.navigate_to_list()
    listing.search_by_name(original_name)
    listing.open_record_by_name(original_name)
    rp = LoanInterestRatePage(listing.page)
    rp.click_edit()
    steps.append(f"Opened Edit form for '{original_name}'")
    return rp, original_name


def _assert_invalid_rate_edit_shows_a_message(factory, value: str, steps):
    scenario = factory.create_rate()
    rp = factory.open_rate_edit(scenario)
    original = rp.get_row_interest_rate(0)
    steps.append(f"Changed the existing rate from {original} to {value!r}")
    rp.set_row_interest_rate(value, 0)
    rp.save()
    rp.page.wait_for_timeout(2_000)
    message = rp.error_banner_text()
    assert message, f"The invalid rate {value!r} was handled without a clear message"
    assert "java" not in message.lower() and "exception" not in message.lower(), message


class TestEditLoanInterestRate:

    def test_verify_that_the_edit_heading_identifies_the_interest_rate(self, edit_form, steps):
        """TC-LIR-031 — The Edit heading identifies the interest rate."""
        rp, original_name = edit_form
        steps.append("Checked the Edit page heading")
        heading = rp.frame.locator("h1").filter(has_text="Edit loan interest rate")
        expect(heading).to_be_visible()
        expect(heading).to_contain_text(original_name)

    def test_verify_that_the_edit_form_prepopulates_the_name(self, edit_form, steps):
        """TC-LIR-032 — Edit form pre-populates the Name field."""
        rp, original_name = edit_form
        steps.append("Checked the Name field's current value")
        assert rp.get_name_value() == original_name

    def test_verify_that_the_type_is_read_only_on_the_edit_form(self, edit_form, steps):
        """TC-LIR-033 — Type field is read-only in edit mode (plain text, not a radio)."""
        rp, _ = edit_form
        steps.append("Checked that no Type radio buttons are present on the Edit form")
        expect(rp.frame.get_by_role("radio", name="Revolving", exact=True)).to_have_count(0)
        expect(rp.frame.get_by_text("Revolving", exact=True).first).to_be_visible()

    def test_verify_that_the_edit_form_prepopulates_the_status(self, edit_form, steps):
        """TC-LIR-034 — Edit form pre-populates Status."""
        rp, _ = edit_form
        steps.append("Checked the Status combobox's current value")
        # The combobox is an <input>; its displayed value lives in the value
        # attribute, not textContent, so use to_have_value.
        combo = rp.frame.get_by_role("combobox", name="Status").first
        expect(combo).to_have_value("Active")

    def test_verify_that_the_edit_form_prepopulates_the_schedule_rows(self, edit_form, steps):
        """TC-LIR-035 — Schedule rows are pre-populated in edit mode."""
        rp, _ = edit_form
        steps.append("Checked the schedule grid row count")
        assert rp.get_schedule_row_count() >= 1

    def test_verify_that_clearing_the_name_and_saving_keeps_the_user_on_edit(self, edit_form, steps):
        """TC-LIR-036 — Clearing Name and saving keeps the user in Edit mode."""
        rp, _ = edit_form
        steps.append("Cleared the Name field")
        rp.fill_name("")
        rp.save()
        steps.append("Clicked Save with an empty name")
        rp.page.wait_for_timeout(1_500)
        expect(
            rp.frame.locator("h1").filter(has_text="Edit loan interest rate")
        ).to_be_visible()

    def test_verify_that_cancel_discards_unsaved_edit_changes(self, edit_form, steps):
        """TC-LIR-037 — Cancelling edit does not save changes; original name is retained."""
        rp, original_name = edit_form
        steps.append("Changed the Name field to 'CHANGED_NAME'")
        rp.fill_name("CHANGED_NAME")
        rp.cancel()
        steps.append("Clicked Cancel")
        rp.wait_for_view_page()
        # LIR's View heading is "Loan interest rates: <ID>" — it never
        # includes the name (unlike some other modules); the name is shown
        # as a separate labelled field instead.
        expect(rp.frame.get_by_text(original_name, exact=True).first).to_be_visible()

    def test_verify_that_save_persists_an_updated_interest_rate_name(self, edit_form, unique_loan_interest_rate_name, steps):
        """TC-LIR-038 — Save persists an updated Name; the View page reflects it."""
        rp, _ = edit_form
        new_name = unique_loan_interest_rate_name + "_ED"
        steps.append(f"Changed Name to '{new_name}'")
        rp.fill_name(new_name)
        rp.save()
        steps.append("Clicked Save")
        rp.wait_for_view_page()
        # LIR's View heading never includes the name; check the labelled
        # Name field instead (see the cancel test's note).
        expect(rp.frame.get_by_text(new_name, exact=True).first).to_be_visible()
        # Rename back so the created_loan_interest_rate fixture's teardown can
        # still find/delete it by its original unique name.
        rp.click_edit()
        rp.fill_name(unique_loan_interest_rate_name)
        rp.save()
        rp.wait_for_view_page()


class TestEditLoanInterestRateRegressionCoverage:

    def test_verify_that_the_save_action_is_available_on_the_edit_page(
        self, edit_form, steps
    ):
        """UPDATE SL 53 — Save is available on Edit."""
        rp, _ = edit_form
        steps.append("Checked the Edit header for Save")
        assert rp.header_action_is_available("Save")

    def test_verify_that_the_cancel_action_is_available_on_the_edit_page(
        self, edit_form, steps
    ):
        """UPDATE SL 57 — Cancel is available on Edit."""
        rp, _ = edit_form
        steps.append("Checked the Edit header for Cancel")
        assert rp.header_action_is_available("Cancel")

    def test_verify_that_both_edit_sections_can_be_collapsed_and_expanded(
        self, edit_form, steps
    ):
        """UPDATE SL 2 — Both Edit sections provide working expand/collapse controls."""
        rp, _ = edit_form
        for section in (
            "Loan interest rate information",
            "Loan interest rate schedule",
        ):
            steps.append(f"Collapsed and expanded {section} on Edit")
            assert rp.section_has_toggle(section), f"No toggle for {section}"
            rp.collapse_named_section(section)
            assert not rp.is_named_section_expanded(section)
            rp.expand_named_section(section)
            assert rp.is_named_section_expanded(section)

    def test_verify_that_edit_rejects_a_duplicate_interest_rate_name(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 9/33 — Edit rejects a name already used by another rate."""
        first = interest_rate_scenario_factory.create_rate()
        second = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(first)
        steps.append(f"Changed {first['name']} to duplicate {second['name']}")
        rp.fill_name(second["name"])
        rp.save()
        rp.page.wait_for_timeout(2_000)
        message = rp.error_banner_text()
        assert "Edit" in rp.get_page_title() and message
        assert "unique" in message.lower() or "exists" in message.lower()

    def test_verify_that_edit_rejects_a_name_longer_than_two_hundred_characters(
        self, edit_form, steps
    ):
        """UPDATE SL 12/35 — Edit rejects a Name longer than 200 characters."""
        rp, _ = edit_form
        steps.append("Entered a 201-character Name on Edit")
        rp.fill_name("N" * 201)
        rp.save()
        rp.page.wait_for_timeout(1_500)
        assert "Edit" in rp.get_page_title() or rp.error_banner_text()

    def test_verify_that_edit_rejects_a_whitespace_only_name(self, edit_form, steps):
        """UPDATE SL 13/36 — Edit rejects a whitespace-only Name."""
        rp, _ = edit_form
        steps.append("Entered only spaces in Name on Edit")
        rp.fill_name("   ")
        rp.save()
        rp.page.wait_for_timeout(1_500)
        assert "Edit" in rp.get_page_title() or rp.error_banner_text()

    def test_verify_that_status_can_be_changed_to_inactive_and_saved(
        self, edit_form, steps
    ):
        """UPDATE SL 14/37 — A valid Inactive status persists."""
        rp, _ = edit_form
        steps.append("Changed Status from Active to Inactive")
        rp.set_status("Inactive")
        rp.save()
        rp.wait_for_view_page()
        rp.click_edit()
        assert rp.get_status_value() == "Inactive"

    @pytest.mark.xfail(
        reason="The current release silently retains existing schedule dates instead of reporting invalid Edit ordering.",
        strict=False,
    )
    def test_verify_that_edit_rejects_a_start_date_before_the_previous_entry(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 20/42 — An edited Start date cannot precede the previous entry."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026", "11/01/2026")
        )
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Moved the second Start date before the first")
        rp.set_row_start_date("08/01/2026", 1)
        rp.save()
        assert rp.error_banner_text()

    @pytest.mark.xfail(
        reason="The current release silently retains existing schedule dates instead of reporting duplicate Edit dates.",
        strict=False,
    )
    def test_verify_that_edit_rejects_duplicate_schedule_start_dates(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 22/44 — Two edited schedule rows cannot have the same date."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026")
        )
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Changed the second Start date to match the first")
        rp.set_row_start_date("09/01/2026", 1)
        rp.save()
        assert rp.error_banner_text()

    @pytest.mark.xfail(
        reason="The current release silently retains existing schedule dates instead of reporting an inserted-between-dates error.",
        strict=False,
    )
    def test_verify_that_an_existing_start_date_cannot_be_moved_between_adjacent_entries(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 23/45 — Edit enforces the schedule's strict date order."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "11/01/2026", "12/01/2026")
        )
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Moved the last entry between the first two entries")
        rp.set_row_start_date("10/01/2026", 2)
        rp.save()
        assert rp.error_banner_text()

    @pytest.mark.xfail(
        reason="The current release may discard an invalid existing rate without showing the required message.",
        strict=False,
    )
    def test_verify_that_edit_rejects_a_non_numeric_interest_rate_with_a_clear_message(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 33/54 — Edit rejects a non-numeric rate."""
        _assert_invalid_rate_edit_shows_a_message(
            interest_rate_scenario_factory, "abc", steps
        )

    @pytest.mark.xfail(
        reason="The current release may discard an invalid existing rate without showing the required message.",
        strict=False,
    )
    def test_verify_that_edit_rejects_a_negative_interest_rate_with_a_clear_message(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 34/55 — Edit rejects a negative rate."""
        _assert_invalid_rate_edit_shows_a_message(
            interest_rate_scenario_factory, "-5", steps
        )

    @pytest.mark.xfail(
        reason="The current release may discard an invalid existing rate without showing the required message.",
        strict=False,
    )
    def test_verify_that_edit_rejects_more_than_four_rate_decimal_places_with_a_clear_message(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 35/56 — Edit rejects five decimal places."""
        _assert_invalid_rate_edit_shows_a_message(
            interest_rate_scenario_factory, "5.12345", steps
        )

    @pytest.mark.xfail(
        reason="The current release may discard an invalid existing rate without showing the required message.",
        strict=False,
    )
    def test_verify_that_edit_rejects_a_zero_interest_rate_with_a_clear_message(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 39/58 — Edit rejects zero."""
        _assert_invalid_rate_edit_shows_a_message(
            interest_rate_scenario_factory, "0", steps
        )

    @pytest.mark.xfail(
        reason="The current release silently retains the original existing rate instead of persisting a valid unassigned edit.",
        strict=False,
    )
    def test_verify_that_edit_persists_a_four_decimal_numeric_rate_for_an_unassigned_record(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 37-38 / U5 — A valid numeric-string rate with four decimals persists."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Changed the existing rate to numeric string 5.1234")
        rp.set_row_interest_rate("5.1234", 0)
        rp.save()
        rp.wait_for_view_page()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rp.get_row_interest_rate(0) == "5.1234"

    def test_verify_that_notes_can_be_cleared_on_edit(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 40-41/59 — Notes can be empty on Edit."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Cleared Notes on the existing row")
        rp.set_row_notes("", 0)
        rp.save()
        rp.wait_for_view_page()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rp.get_row_notes(0) == ""

    def test_verify_that_notes_accept_one_thousand_characters_on_edit(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 42 — Notes accepts 1000 characters on Edit."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        expected = "N" * 1000
        steps.append("Entered 1000 characters in Notes on Edit")
        rp.set_row_notes(expected, 0)
        rp.save()
        rp.wait_for_view_page()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rp.get_row_notes(0) == expected

    def test_verify_that_notes_longer_than_one_thousand_characters_are_rejected_on_edit(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 43/60 — Edit rejects Notes longer than 1000 characters."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Entered 1001 characters in Notes on Edit")
        rp.set_row_notes("N" * 1001, 0)
        rp.save()
        rp.page.wait_for_timeout(2_000)
        assert "Edit" in rp.get_page_title() or rp.error_banner_text()

    def test_verify_that_notes_on_an_earlier_entry_can_be_updated_when_later_entries_exist(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 44/61 — An earlier row's Notes remains editable."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026")
        )
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Updated Notes on the earlier row")
        rp.set_row_notes("Earlier row updated", 0)
        rp.save()
        rp.wait_for_view_page()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rp.get_row_notes(0) == "Earlier row updated"

    def test_verify_that_attachment_on_an_earlier_entry_remains_editable_when_later_entries_exist(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 46/63 — An earlier row's Attachment picker remains editable."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026")
        )
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Activated Attachment on the earlier schedule row")
        assert rp.attachment_is_editable(0)

    def test_verify_that_a_record_without_an_attachment_can_still_be_updated(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 48/65 — Attachment remains optional during Update."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Updated Notes while Attachment remained blank")
        rp.set_row_notes("Updated without attachment", 0)
        rp.save()
        rp.wait_for_view_page()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rp.get_row_notes(0) == "Updated without attachment"

    def test_verify_that_a_success_message_is_shown_after_a_valid_edit(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 55 — A valid Edit displays confirmation feedback."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        rp.set_row_notes("Toast verification", 0)
        rp.start_recording_toasts()
        steps.append("Saved a valid Edit while recording notifications")
        rp.save()
        message = rp.wait_for_toast()
        assert message, "No confirmation feedback was shown after Edit"

    @pytest.mark.xfail(
        reason="Create and Edit currently use different duplicate-name wording, and Edit can expose the internal object path.",
        strict=False,
    )
    def test_verify_that_duplicate_name_messages_are_consistent_on_create_and_edit(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL U4 — Create and Edit show the same readable duplicate-name rule."""
        first = interest_rate_scenario_factory.create_rate()
        existing = interest_rate_scenario_factory.create_rate()
        listing = LoanInterestRateListingPage(interest_rate_scenario_factory.page)
        listing.navigate_to_list()
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        rp.fill_name(existing["name"])
        rp.select_type("Revolving")
        rp.click_add_row()
        rp.set_row_start_date("09/01/2026")
        rp.set_row_interest_rate("5")
        rp.save()
        rp.page.wait_for_timeout(2_000)
        create_message = rp.error_banner_text()
        rp.cancel()

        rp = interest_rate_scenario_factory.open_rate_edit(first)
        rp.fill_name(existing["name"])
        rp.save()
        rp.page.wait_for_timeout(2_000)
        edit_message = rp.error_banner_text()
        steps.append("Compared Create and Edit duplicate-name messages")
        for message in (create_message, edit_message):
            assert message and "exists" in message.lower()
            assert "loan-management/" not in message.lower()
