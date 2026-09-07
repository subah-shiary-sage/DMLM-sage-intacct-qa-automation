"""Business rules for revolving and non-revolving interest-rate schedules."""

import pytest

from .conftest import ASSIGNED_ORIGINATION_DATE


def _assert_readable_error(rate_page, expected_words: tuple[str, ...]) -> str:
    rate_page.page.wait_for_timeout(2_000)
    message = rate_page.error_banner_text()
    assert message, "the action was blocked without an explanation"
    lowered = message.lower()
    assert any(word.lower() in lowered for word in expected_words), message
    assert "loan-management/" not in lowered, message
    return message


class TestRevolvingSingleEntryRateRules:

    def test_verify_that_all_supported_fields_are_editable_before_a_revolving_rate_is_assigned(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-044 — All supported fields remain editable before assignment."""
        scenario = interest_rate_scenario_factory.create_rate()
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Checked every supported Edit field before assigning the rate")
        assert rate_page.is_name_editable()
        assert rate_page.status_is_editable()
        assert rate_page.schedule_field_is_editable(0, "start_date")
        assert rate_page.schedule_field_is_editable(0, "interest_rate")
        assert rate_page.schedule_field_is_editable(0, "notes")
        assert rate_page.attachment_is_editable(0)
        assert rate_page.add_row_is_enabled()
        assert rate_page.row_remove_is_enabled(0)

    def test_verify_that_the_rate_value_cannot_be_updated_after_assignment_to_a_loan(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-045 — An assigned revolving rate value cannot be changed."""
        scenario = interest_rate_scenario_factory.create_rate()
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        original = rate_page.get_row_interest_rate(0)
        steps.append("Attempted to change the only rate entry after loan assignment")
        if rate_page.schedule_field_is_editable(0, "interest_rate"):
            rate_page.set_row_interest_rate("8.25", 0)
            rate_page.save()
            rate_page.page.wait_for_timeout(2_000)
            if "Edit" in rate_page.get_page_title():
                rate_page.cancel()
                rate_page.wait_for_view_page()
            else:
                rate_page.wait_for_view_page()
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rate_page.get_row_interest_rate(0) == original

    @pytest.mark.xfail(
        reason="The current release silently retains the original assigned start "
        "date instead of accepting valid back/forward dates and showing an "
        "origination-boundary message.",
        strict=False,
    )
    def test_verify_that_the_earliest_assigned_start_date_can_move_backward_or_forward_but_not_past_origination(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-046 — Assigned earliest date may move but not past origination."""
        scenario = interest_rate_scenario_factory.create_rate()
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)

        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Moved the earliest date backward and saved")
        rate_page.set_row_start_date("08/01/2026", 0)
        rate_page.save()
        rate_page.wait_for_view_page()

        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Moved the earliest date forward while keeping it before origination")
        rate_page.set_row_start_date("11/01/2026", 0)
        rate_page.save()
        rate_page.wait_for_view_page()

        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Moved the earliest date later than the assigned loan origination date")
        rate_page.set_row_start_date("01/01/2027", 0)
        rate_page.save()
        message = _assert_readable_error(rate_page, ("origination", "start date"))
        assert ASSIGNED_ORIGINATION_DATE.split("/")[-1] in message or "origination" in message.lower()

    @pytest.mark.xfail(
        reason="The current release blocks deleting the assigned entry as expected "
        "but also rejects adding the permitted later entry.",
        strict=False,
    )
    def test_verify_that_an_assigned_entry_cannot_be_deleted_but_a_new_entry_can_be_added(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-047 — Assigned entries stay, while later entries may be added."""
        scenario = interest_rate_scenario_factory.create_rate()
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)

        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Attempted to delete the assigned schedule entry")
        rate_page.click_remove_row(0)
        rate_page.save()
        _assert_readable_error(rate_page, ("loan", "assigned", "used", "earliest"))
        rate_page.cancel()
        rate_page.wait_for_view_page()

        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Added a later schedule entry without deleting the assigned entry")
        rate_page.click_add_row()
        new_index = rate_page.get_schedule_row_count() - 1
        rate_page.set_row_start_date("01/01/2027", new_index)
        rate_page.set_row_interest_rate("6.25", new_index)
        rate_page.save()
        rate_page.wait_for_view_page()
        assert rate_page.get_schedule_row_count() == 2

    @pytest.mark.xfail(
        reason="The current release does not persist a future-date change for a "
        "later entry on an assigned revolving rate.",
        strict=False,
    )
    def test_verify_that_every_entry_after_the_earliest_can_move_to_a_future_start_date(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-048 — Later assigned entries may move to any future month."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026")
        )
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Moved the second entry beyond the loan origination month")
        rate_page.set_row_start_date("02/01/2027", 1)
        rate_page.save()
        rate_page.wait_for_view_page()
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rate_page.get_row_start_date(1) == "02/01/2027"


class TestRevolvingMultiEntryRateRules:

    def test_verify_that_the_earliest_unassigned_entry_cannot_be_deleted_and_shows_a_clear_error(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-049 — The earliest unassigned entry cannot be removed."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026", "11/01/2026")
        )
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Removed the earliest row and attempted to save")
        rate_page.click_remove_row(0)
        rate_page.save()
        _assert_readable_error(rate_page, ("earliest entry",))

    def test_verify_that_only_the_latest_unassigned_entry_can_be_removed(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-050 — Middle rows stay and only the latest row can be removed."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026", "11/01/2026")
        )
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Attempted to remove the middle entry")
        rate_page.click_remove_row(1)
        rate_page.save()
        _assert_readable_error(
            rate_page, ("latest entry", "most recent", "end of the schedule", "later entries")
        )
        rate_page.cancel()
        rate_page.wait_for_view_page()

        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Removed the latest entry")
        rate_page.click_remove_row(rate_page.get_schedule_row_count() - 1)
        rate_page.save()
        rate_page.wait_for_view_page()
        assert rate_page.get_schedule_row_count() == 2

    @pytest.mark.xfail(
        reason="The current release accepts Save but silently retains all original "
        "start dates for an unassigned multi-entry rate.",
        strict=False,
    )
    def test_verify_that_every_unassigned_entry_start_date_can_be_updated(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-051 — Every unassigned entry accepts a valid new start date."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026", "11/01/2026")
        )
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        expected = ["08/01/2026", "09/01/2026", "10/01/2026"]
        steps.append("Moved every unassigned entry while preserving date order")
        for index, date in enumerate(expected):
            rate_page.set_row_start_date(date, index)
        rate_page.save()
        rate_page.wait_for_view_page()
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert [rate_page.get_row_start_date(i) for i in range(3)] == expected

    @pytest.mark.xfail(
        reason="The current release silently retains assigned schedule dates instead "
        "of allowing valid edits and reporting only dates beyond origination.",
        strict=False,
    )
    def test_verify_that_assigned_multi_entry_dates_can_move_but_none_can_move_past_origination(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-052 — Assigned multi-entry dates cannot pass origination."""
        scenario = interest_rate_scenario_factory.create_rate(
            dates=("09/01/2026", "10/01/2026", "11/01/2026")
        )
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        valid_dates = ["08/01/2026", "09/01/2026", "11/01/2026"]
        steps.append("Moved all entries to valid months on or before origination")
        for index, date in enumerate(valid_dates):
            rate_page.set_row_start_date(date, index)
        rate_page.save()
        rate_page.wait_for_view_page()

        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        steps.append("Moved an assigned entry later than origination")
        rate_page.set_row_start_date("01/01/2027", 0)
        rate_page.save()
        _assert_readable_error(rate_page, ("origination", "start date"))


class TestNonRevolvingRateRules:

    def test_verify_that_a_non_revolving_rate_value_cannot_be_updated_even_when_unassigned(
        self, interest_rate_scenario_factory, steps
    ):
        """TC-LIR-053 — An unassigned non-revolving rate value is immutable."""
        scenario = interest_rate_scenario_factory.create_rate(rate_type="Non-revolving")
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        original = rate_page.get_row_interest_rate(0)
        steps.append("Attempted to change an unassigned Non-revolving rate")
        if rate_page.schedule_field_is_editable(0, "interest_rate"):
            rate_page.set_row_interest_rate("8.25", 0)
            rate_page.save()
            rate_page.page.wait_for_timeout(2_000)
            if "Edit" in rate_page.get_page_title():
                # The current release may block this silently or show a
                # validation message. The business rule only requires that
                # the stored value does not change.
                rate_page.cancel()
                rate_page.wait_for_view_page()
            else:
                rate_page.wait_for_view_page()
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        assert rate_page.get_row_interest_rate(0) == original


class TestStatusAndLoanAssignmentRules:

    def test_verify_that_reactivating_an_interest_rate_allows_it_to_be_assigned_to_a_loan(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 15/38 — Inactive-to-Active allows new loan assignment."""
        scenario = interest_rate_scenario_factory.create_rate()
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        rate_page.set_status("Inactive")
        rate_page.save()
        rate_page.wait_for_view_page()
        rate_page.click_edit()
        rate_page.set_status("Active")
        rate_page.save()
        rate_page.wait_for_view_page()
        steps.append("Reactivated the rate and assigned it to a temporary revolving loan")
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)
        assert scenario["loan_name"]

    def test_verify_that_an_inactive_interest_rate_cannot_be_selected_for_a_new_loan(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 16/39 — Active-to-Inactive prevents new loan assignment."""
        scenario = interest_rate_scenario_factory.create_rate()
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        rate_page.set_status("Inactive")
        rate_page.save()
        rate_page.wait_for_view_page()

        from pages.loan_account.listing_page import LoanAccountListingPage

        listing = LoanAccountListingPage(rate_page.page)
        listing.navigate_to_list()
        listing.click_create()
        combo = listing.frame.get_by_role("combobox", name="Interest rate").first
        combo.click()
        combo.fill(scenario["name"])
        rate_page.page.wait_for_timeout(1_500)
        steps.append("Searched the Loan Interest rate picker for the inactive rate")
        assert listing.frame.get_by_role(
            "option", name=scenario["name"], exact=False
        ).count() == 0

    def test_verify_that_an_existing_loan_keeps_its_rate_after_the_rate_is_made_inactive(
        self, interest_rate_scenario_factory, steps
    ):
        """UPDATE SL 17/40 — Inactive status does not detach existing loans."""
        scenario = interest_rate_scenario_factory.create_rate()
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)
        rate_page = interest_rate_scenario_factory.open_rate_edit(scenario)
        rate_page.set_status("Inactive")
        rate_page.save()
        rate_page.wait_for_view_page()

        from pages.loan_account.listing_page import LoanAccountListingPage

        listing = LoanAccountListingPage(rate_page.page)
        listing.navigate_to_list()
        listing.search_by_account_name(scenario["loan_name"])
        listing.open_record_by_account_name(scenario["loan_name"])
        steps.append("Opened the existing loan after making its rate Inactive")
        assert listing.frame.get_by_text(scenario["name"], exact=False).count() > 0


class TestRateEffectiveDateAssignmentRules:

    def test_verify_that_a_loan_cannot_use_a_rate_that_starts_after_the_loan_origination_date(
        self, interest_rate_scenario_factory, steps
    ):
        """CREATE SL 28 / UPDATE SL 36/57 — Rate effective date must not follow origination."""
        scenario = interest_rate_scenario_factory.create_rate(dates=("12/01/2026",))
        loan_page, _ = interest_rate_scenario_factory.open_revolving_loan_create_using_rate(
            scenario,
            origination_date="11/01/2026",
            select_rate_before_origination=True,
        )
        steps.append("Saved a loan whose origination month precedes the selected rate")
        loan_page.save()
        loan_page.page.wait_for_timeout(2_000)
        message = loan_page.error_banner_text()
        assert "Create" in loan_page.get_page_title() or message
        if message:
            lowered = message.lower()
            assert any(word in lowered for word in ("rate", "start", "effective", "origination"))

    def test_verify_that_an_assigned_interest_rate_record_cannot_be_deleted(
        self, interest_rate_scenario_factory, steps
    ):
        """DELETE SL 3/70 — A rate assigned to a loan cannot be deleted."""
        scenario = interest_rate_scenario_factory.create_rate()
        interest_rate_scenario_factory.assign_to_revolving_loan(scenario)
        rate_page = interest_rate_scenario_factory.reopen_rate_view(scenario)
        steps.append("Attempted to delete the whole assigned interest-rate record")
        rate_page.click_delete()
        rate_page.confirm_delete_in_modal()
        rate_page.page.wait_for_timeout(2_000)
        message = rate_page.error_banner_text()
        assert message, "Assigned rate deletion was not blocked with an explanation"
        assert any(word in message.lower() for word in ("loan", "associated", "assigned"))
