"""
test_schedule_and_blocked.py
=========================
Schedule-grid / Type behaviour for the Loan Interest Rate module, plus explicit
skip stubs for the checklist rows that cannot be executed in this environment.

Verified live against release www-p303 / SNL_release_monthly / LME entity
on 2026-08-17.

Of the checklist's 244 rows, 71 are blocked here. They are represented as
skipped tests with the specific reason rather than omitted, so the coverage gap
stays visible in the report instead of looking like coverage:

  * 40 rows — multi-entity (create/edit/delete/view from root vs child
    location). Only one entity is reachable with these credentials.
  * 14 rows — closed SI period / "interest and statements already generated".
    Needs a period closed or a statement run, which this suite will not do to a
    shared environment.
  *  13 rows — API-level data injection (null vs empty, invalid data type,
    malformed attachmentKey). Not reachable through the UI.
  *  4 rows — direct SNLLOAN* database verification.
"""

import time

import pytest

from pages.loan_interest_rate.rate_page import LoanInterestRatePage

VALID_START_DATE = "09/01/2026"


def _unique(prefix: str = "AutoLIR") -> str:
    return f"{prefix}_{int(time.time() * 1000) % 1000000}"


def _fill_minimum(rp, name, rate="5", start=VALID_START_DATE):
    rp.fill_name(name)
    rp.select_type("Revolving")
    rp.click_add_row()
    rp.set_row_start_date(start)
    rp.set_row_interest_rate(rate)


def _cleanup(listing, rp, name):
    try:
        listing.navigate_to_list()
        listing.search_by_name(name)
        if listing.is_record_visible(name):
            listing.open_record_by_name(name)
            rp.click_delete()
            rp.confirm_delete_in_modal()
            listing.wait_for_list_page()
    except Exception:
        pass


@pytest.fixture()
def create_form(loan_interest_rate_listing_page, steps):
    listing = loan_interest_rate_listing_page
    listing.click_create()
    steps.append("Opened the Loan interest rate Create form")
    return LoanInterestRatePage(listing.page)


class TestTypeAndSchedule:
    """Checklist CREATE SL A1-A5, A10-A11 and SL 12-14."""

    def test_verify_that_the_type_field_is_marked_as_required(self, create_form, steps):
        """SL A1 / A3 — Type is present and mandatory."""
        steps.append("Checked the Type mandatory marker")
        assert create_form.is_field_mandatory("Type")

    def test_verify_that_type_offers_revolving_and_non_revolving_options(self, create_form, steps):
        """SL A2 — Type offers exactly Revolving and Non-revolving."""
        steps.append("Read the Type options")
        labels = [l.rstrip(" *").strip() for l in create_form.field_labels()]
        assert "Revolving" in labels, labels
        assert "Non-revolving" in labels, labels

    def test_verify_that_the_schedule_grid_displays_start_date_rate_and_notes_columns(self, create_form, steps):
        """SL 14 — The schedule grid has Start date, Interest rate and Notes."""
        steps.append("Read the schedule grid column headers")
        headers = create_form.schedule_column_headers()
        joined = " | ".join(headers)
        assert "Start date" in joined, headers
        assert "Interest rate" in joined, headers
        assert "Notes" in joined, headers

    @pytest.mark.xfail(
        reason="SL A9 — the schedule grid exposes raw resource keys "
               "(ROW_VALIDATION_SUMMARY, IA.ATTACHMENT, ROW_MANIPULATION) as column "
               "headers instead of localised labels",
        strict=False,
    )
    def test_verify_that_the_schedule_grid_does_not_display_raw_resource_keys(self, create_form, steps):
        """SL A9 — No raw IA.* / ROW_* keys are shown to the user."""
        steps.append("Scanned the create form for untranslated resource keys")
        leaked = create_form.untranslated_aria_keys()
        assert not leaked, f"untranslated keys present: {sorted(leaked)}"

    def test_verify_that_a_revolving_interest_rate_can_be_created(
        self, loan_interest_rate_listing_page, steps
    ):
        """SL A4 — A rate can be created with Type = Revolving."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRRev")
        steps.append("Created a Revolving rate")
        _fill_minimum(rp, name)
        rp.save()
        try:
            rp.wait_for_view_page()
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_a_non_revolving_interest_rate_can_be_created_with_one_entry(
        self, loan_interest_rate_listing_page, steps
    ):
        """SL A5 / A10 — A Non-revolving rate saves with a single schedule row."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRNonRev")
        steps.append("Created a Non-revolving rate with one schedule row")
        rp.fill_name(name)
        rp.select_type("Non-revolving")
        rp.click_add_row()
        rp.set_row_start_date(VALID_START_DATE)
        rp.set_row_interest_rate("5")
        rp.save()
        try:
            rp.wait_for_view_page()
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_a_revolving_interest_rate_accepts_multiple_schedule_entries(
        self, loan_interest_rate_listing_page, steps
    ):
        """SL A11 — A Revolving rate accepts multiple ascending schedule rows."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRMulti")
        steps.append("Created a Revolving rate with two ascending schedule rows")
        rp.fill_name(name)
        rp.select_type("Revolving")
        for _ in range(2):
            rp.click_add_row()
        rp.set_row_start_date("09/01/2026", row_index=0)
        rp.set_row_interest_rate("5", row_index=0)
        rp.set_row_start_date("10/01/2026", row_index=1)
        rp.set_row_interest_rate("6", row_index=1)
        rp.save()
        try:
            rp.wait_for_view_page()
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_creating_an_interest_rate_shows_a_confirmation_message(
        self, loan_interest_rate_listing_page, steps
    ):
        """
        SL 53 — A success message appears when the rate is saved.

        The toast is short-lived, so recording is armed before Save.
        """
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRToast")
        _fill_minimum(rp, name)
        steps.append("Armed the toast recorder, then saved")
        rp.start_recording_toasts()
        rp.save()
        toast = rp.wait_for_toast()
        try:
            assert toast, "no confirmation message was shown after creating a rate"
            steps.append(f"Confirmation message: {toast!r}")
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_the_save_menu_contains_all_expected_options(self, create_form, steps):
        """SL 49 — Save offers Save / Save and new / Save and close."""
        steps.append("Opened the Save split-button menu")
        opts = [o.lower() for o in create_form.save_menu_options()]
        for wanted in ("save", "save and close", "save and new"):
            assert any(o == wanted for o in opts), f"{wanted!r} missing from {opts}"

    @pytest.mark.xfail(
        reason="SL A7 — 'Save and new' leaves the previous schedule rows in the grid "
               "instead of presenting a fully blank form",
        strict=False,
    )
    def test_verify_that_save_and_new_opens_a_blank_schedule_grid(
        self, loan_interest_rate_listing_page, steps
    ):
        """SL A7 / SL 51 — "Save and new" must present a fully blank form."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRSaveNew")
        _fill_minimum(rp, name)
        steps.append("Saved using 'Save and new' and inspected the fresh form")
        rp.save_via("Save and new")
        rp.page.wait_for_timeout(3_000)
        try:
            assert rp.get_schedule_row_count() == 0, (
                f"the new form still shows {rp.get_schedule_row_count()} schedule row(s)"
            )
        finally:
            _cleanup(listing, rp, name)


class TestBlockedMultiEntity:
    """
    40 checklist rows covering create / update / delete / view of a rate and of
    individual schedule entries across root and child locations.
    """

    REASON = (
        "Multi-entity scenario — needs both a root (top-level) and a child entity. "
        "These credentials reach a single entity (LME), so root-vs-child behaviour "
        "cannot be exercised. Verify manually in a multi-entity company."
    )

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_interest_rate_can_be_created_in_the_root_location(self):
        """CREATE SL 36/46, VALIDATION SL 23 — Create in the root location."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_interest_rate_can_be_created_in_a_child_location(self):
        """CREATE SL 37/47, VALIDATION SL 24 — Create in a child location."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_interest_rate_can_be_updated_across_locations(self):
        """UPDATE SL 24-30, 46-52 — Update a rate/entry across root and child."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_interest_rate_can_be_deleted_across_locations(self):
        """DELETE SL 4, 8-13, 72, 76-81 — Delete a rate/entry across locations."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_interest_rate_can_be_viewed_across_locations(self):
        """VIEW SL 17-19, 21-23 — View a rate/entry from root and child levels."""


class TestBlockedClosedPeriod:
    """
    14 checklist rows depending on a closed Sage Intacct period, or on interest
    and statements already generated for the rate.
    """

    REASON = (
        "Needs a closed SI period or a completed interest/statement run. Closing a "
        "period or generating statements would alter shared release data, so this "
        "suite does not create that state. Verify manually or seed a dedicated company."
    )

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_a_start_date_in_a_closed_period_is_rejected(self):
        """CREATE SL 18/20, VALIDATION SL 7/9 — Start date inside a closed period."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_start_dates_are_locked_after_statements_are_generated(self):
        """UPDATE SL 19/41 — Start date is locked once statements exist."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_notes_remain_editable_in_a_closed_period(self):
        """UPDATE SL 45/62 — Notes remain editable inside a closed period."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_attachments_remain_editable_in_a_closed_period(self):
        """UPDATE SL 47/64 — Attachment remains editable inside a closed period."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_entry_in_a_closed_period_cannot_be_deleted(self):
        """DELETE SL 2/71 — An entry inside a closed period cannot be deleted."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_schedule_entries_cannot_be_deleted_after_statements_are_generated(self):
        """DELETE SL 5-6, 73-74 — Schedule-line delete once statements exist."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_the_closed_period_start_date_error_is_clear_and_non_technical(self):
        """CREATE SL 54.1 — Closed-period validation uses readable wording."""


class TestBlockedApiLevel:
    """
    13 checklist rows that require sending a malformed or typed payload directly
    to the API — the UI cannot produce them.
    """

    REASON = (
        "API-level only — requires posting a malformed/typed payload (invalid data "
        "type, explicit null vs empty string, non-existent attachmentKey). The UI "
        "cannot produce these requests. Cover with an API test instead."
    )

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_invalid_name_data_type_is_rejected(self):
        """CREATE SL 10 — Name sent as an invalid data type."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_explicitly_null_rate_is_rejected(self):
        """CREATE SL 24, UPDATE SL 32/53 — Rate sent as an explicit null."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_explicitly_null_notes_are_handled_correctly(self):
        """CREATE SL 33, UPDATE SL 41/59 — Notes sent as an explicit null."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_invalid_attachment_key_is_rejected(self):
        """CREATE SL 43-45, UPDATE SL 49-52, 66-68 — attachmentKey validation."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_explicitly_null_name_is_rejected_on_edit(self):
        """UPDATE SL 11/34 — Name sent as explicit null is rejected."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_an_explicitly_null_attachment_is_allowed_on_edit(self):
        """UPDATE SL 49/66 — Attachment sent as explicit null is accepted."""


class TestBlockedAttachmentData:
    """Attachment-list scenarios need controlled active/inactive attachment data."""

    REASON = (
        "Needs known active, inactive, and non-existent attachment records. The shared "
        "release entity does not provide a controlled attachment fixture. Seed those "
        "records before running this scenario."
    )

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_a_valid_attachment_can_be_selected_when_creating_a_rate(self):
        """CREATE SL 43 — A valid active attachment key is accepted."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_inactive_attachments_are_absent_from_the_create_picker(self):
        """CREATE SL 44 / VALIDATION SL 26 — Inactive attachments are not listed."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_invalid_attachments_are_absent_from_the_create_picker(self):
        """CREATE SL 45 / VALIDATION SL 27 — Invalid attachments are not listed."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_a_valid_attachment_can_be_selected_when_editing_a_rate(self):
        """UPDATE SL 52 — A valid active attachment key is accepted on Edit."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_invalid_attachments_are_absent_from_the_edit_picker(self):
        """UPDATE SL 50/67 — Invalid attachments are not listed on Edit."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_inactive_attachments_are_absent_from_the_edit_picker(self):
        """UPDATE SL 51/68 — Inactive attachments are not listed on Edit."""


class TestBlockedDatabase:
    """4 checklist rows verifying SNLLOAN* table state directly."""

    REASON = (
        "Database-level — needs a direct Oracle query via integrations/db.py "
        "(ORACLE_* credentials), not the UI."
    )

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_the_database_is_updated_when_an_interest_rate_is_created(self):
        """CREATE SL 38 — The database reflects the new rate."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_the_database_is_updated_when_an_interest_rate_is_changed(self):
        """UPDATE SL 31 — The database reflects the updated rate."""

    @pytest.mark.skip(reason=REASON)
    def test_verify_that_the_database_is_updated_when_an_interest_rate_is_deleted(self):
        """DELETE SL 7/75 — The database reflects the deleted rate."""
