"""
test_validation.py
=========================
Field-validation coverage for the Loan Interest Rate module — the checklist
rows the existing TC-LIR-001–043 files do not reach.

Checklist: "Loan Interest Rate - CRUD" (244 rows). Those 244 contain 106
verbatim duplicates (the VALIDATION / UPDATE / DELETE sections from row 156
repeat the earlier CREATE / UPDATE / DELETE ones), so each test here names
every checklist row it satisfies rather than repeating the same click path.

Verified against release www-p303 / SNL_release_monthly / LME entity. The
current regression requirements allow four decimal places, reject five or
more decimal places, and reject zero.
"""

import time

import pytest

from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
from pages.loan_interest_rate.rate_page import LoanInterestRatePage

NAME_MAX = 200
NOTES_MAX = 1000
VALID_START_DATE = "09/01/2026"   # must be the first day of a month
JSON_POINTER = "/loanInterestRateEntries/"


def _unique(prefix: str = "AutoLIR") -> str:
    return f"{prefix}_{int(time.time() * 1000) % 1000000}"


def _fill_minimum(rate_page, name: str, rate: str = "5", start: str = VALID_START_DATE):
    """Name + Type + one schedule row is the minimum a rate needs to save."""
    rate_page.fill_name(name)
    rate_page.select_type("Revolving")
    rate_page.click_add_row()
    rate_page.set_row_start_date(start)
    rate_page.set_row_interest_rate(rate)


def _cleanup(listing, rate_page, name: str) -> None:
    try:
        listing.navigate_to_list()
        listing.search_by_name(name)
        if listing.is_record_visible(name):
            listing.open_record_by_name(name)
            rate_page.click_delete()
            rate_page.confirm_delete_in_modal()
            listing.wait_for_list_page()
    except Exception:
        pass


@pytest.fixture()
def create_form(loan_interest_rate_listing_page, steps):
    listing = loan_interest_rate_listing_page
    listing.click_create()
    steps.append("Opened the Loan interest rate Create form")
    return LoanInterestRatePage(listing.page)


class TestNameValidation:
    """Checklist CREATE SL 4-9 and their VALIDATION-section duplicates."""

    def test_verify_that_the_name_field_is_marked_as_required(self, create_form, steps):
        """CREATE SL 4 — Name is mandatory."""
        steps.append("Checked the Name mandatory marker")
        assert create_form.is_field_mandatory("Name")

    def test_verify_that_the_name_field_accepts_200_characters(
        self, loan_interest_rate_listing_page, steps
    ):
        """CREATE SL 5 — A rate saves with a 200-character name."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = "N" * NAME_MAX
        steps.append(f"Created a rate with a {NAME_MAX}-character name")
        _fill_minimum(rp, name)
        rp.save()
        try:
            rp.wait_for_view_page()
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_a_duplicate_interest_rate_name_is_rejected(
        self, loan_interest_rate_listing_page, steps
    ):
        """CREATE SL 6 / VALIDATION SL 1 — A duplicate name is rejected."""
        listing = loan_interest_rate_listing_page
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRDup")
        try:
            listing.click_create()
            _fill_minimum(rp, name)
            rp.save()
            rp.wait_for_view_page()

            steps.append("Attempted a second rate with the identical name")
            listing.navigate_to_list()
            listing.click_create()
            _fill_minimum(rp, name)
            rp.save()
            rp.page.wait_for_timeout(2_500)
            assert "Create" in rp.get_page_title() or rp.error_banner_text(), (
                "a duplicate name appears to have saved"
            )
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_a_whitespace_only_name_is_rejected(self, create_form, steps):
        """CREATE SL 8 / VALIDATION SL 3 — A whitespace-only name is rejected."""
        steps.append("Saved with a whitespace-only name")
        _fill_minimum(create_form, "   ")
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_a_name_longer_than_200_characters_is_rejected(self, create_form, steps):
        """CREATE SL 9 / VALIDATION SL 4 — A name over 200 characters is rejected."""
        steps.append(f"Saved with a {NAME_MAX + 1}-character name")
        _fill_minimum(create_form, "N" * (NAME_MAX + 1))
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()


class TestRateValidation:
    """Checklist CREATE SL 22-31 and their VALIDATION/UPDATE duplicates."""

    @pytest.mark.xfail(
        reason="SL 22 (already Failed on the checklist) — the rate is enforced as "
               "mandatory on save, but its grid column header carries no red "
               "asterisk, so the requirement is invisible before submitting. "
               "Confirmed live 2026-08-17: header reads 'Interest rate (%)'.",
        strict=False,
    )
    def test_verify_that_the_rate_column_is_marked_as_required(self, create_form, steps):
        """CREATE SL 22 — The rate column should carry the mandatory marker."""
        steps.append("Read the schedule grid column headers")
        headers = create_form.schedule_column_headers()
        rate_header = next((h for h in headers if "Interest rate" in h), "")
        assert rate_header, f"no Interest rate column found in {headers}"
        assert "*" in rate_header, (
            f"the rate column header {rate_header!r} carries no mandatory marker"
        )

    def test_verify_that_a_missing_interest_rate_is_rejected(self, create_form, steps):
        """CREATE SL 23-24 / VALIDATION SL 12-13 — A missing rate is rejected."""
        steps.append("Saved a schedule row with no rate")
        create_form.fill_name(_unique("AutoLIRNoRate"))
        create_form.select_type("Revolving")
        create_form.click_add_row()
        create_form.set_row_start_date(VALID_START_DATE)
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_a_non_numeric_interest_rate_is_rejected(self, create_form, steps):
        """CREATE SL 25 / VALIDATION SL 14 — A non-numeric rate is rejected."""
        steps.append("Entered 'abc' as the rate")
        _fill_minimum(create_form, _unique("AutoLIRAlpha"), rate="abc")
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_a_negative_interest_rate_is_rejected(self, create_form, steps):
        """CREATE SL 26 / VALIDATION SL 15 — A negative rate is rejected."""
        steps.append("Entered -5 as the rate")
        _fill_minimum(create_form, _unique("AutoLIRNeg"), rate="-5")
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        banner = create_form.error_banner_text()
        assert "Create" in create_form.get_page_title() or banner
        if banner:
            steps.append(f"Rejection message: {banner[:120]!r}")

    def test_verify_that_an_interest_rate_accepts_two_decimal_places(
        self, loan_interest_rate_listing_page, steps
    ):
        """CREATE SL 29 — The rate field accepts a numeric value with 2 decimals."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIR2dp")
        steps.append("Created a rate of 5.12")
        _fill_minimum(rp, name, rate="5.12")
        rp.save()
        try:
            rp.wait_for_view_page()
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_an_interest_rate_accepts_four_decimal_places(
        self, loan_interest_rate_listing_page, steps
    ):
        """CREATE SL 30 / UPDATE SL 38 — The rate should allow 4 decimal places."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIR4dp")
        steps.append("Created a rate of 5.1234")
        try:
            _fill_minimum(rp, name, rate="5.1234")
            rp.save()
            rp.page.wait_for_timeout(2_500)
            banner = rp.error_banner_text()
            assert "Create" not in rp.get_page_title(), (
                f"a 4-decimal rate was rejected: {banner[:140]!r}"
            )
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_an_interest_rate_of_zero_is_rejected(self, loan_interest_rate_listing_page, steps):
        """CREATE SL 31 / VALIDATION SL 20 — A rate of 0 must be rejected."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRZero")
        steps.append("Entered 0 as the rate")
        try:
            _fill_minimum(rp, name, rate="0")
            rp.save()
            rp.page.wait_for_timeout(2_500)
            assert "Create" in rp.get_page_title() or rp.error_banner_text(), (
                "a rate of 0 saved successfully"
            )
        finally:
            _cleanup(listing, rp, name)

    @pytest.mark.xfail(
        reason="SL A8 — over-precision rejection can surface a raw JSON pointer and regex "
               "instead of a user-facing message",
        strict=False,
    )
    def test_verify_that_the_rate_precision_error_is_easy_to_understand(self, create_form, steps):
        """CREATE SL 27 / SL A8 — The over-precision message should be readable."""
        steps.append("Entered a 5-decimal rate and read the error")
        _fill_minimum(create_form, _unique("AutoLIRMsg"), rate="5.12345")
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        banner = create_form.error_banner_text()
        assert banner, "no error was shown for an over-precision rate"
        assert JSON_POINTER not in banner, f"message exposes a JSON pointer: {banner!r}"
        assert "pattern" not in banner.lower(), f"message exposes a regex: {banner!r}"


class TestStartDateValidation:
    """Checklist CREATE SL 15-21, 39 and their duplicates."""

    def test_verify_that_a_start_date_must_be_the_first_day_of_a_month(self, create_form, steps):
        """CREATE SL 39 / VALIDATION SL 11 — A non-first-of-month start date fails."""
        steps.append("Entered a mid-month start date")
        _fill_minimum(create_form, _unique("AutoLIRMid"), start="09/15/2026")
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_a_missing_start_date_is_rejected(self, create_form, steps):
        """CREATE SL 19 / VALIDATION SL 8 — A missing start date is rejected."""
        steps.append("Saved a schedule row with no start date")
        create_form.fill_name(_unique("AutoLIRNoDate"))
        create_form.select_type("Revolving")
        create_form.click_add_row()
        create_form.set_row_interest_rate("5")
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_duplicate_schedule_start_dates_are_rejected(self, create_form, steps):
        """CREATE SL 17 / VALIDATION SL 6 — Two rows cannot share a start date."""
        steps.append("Added two schedule rows with the same start date")
        create_form.fill_name(_unique("AutoLIRSameDate"))
        create_form.select_type("Revolving")
        for _ in range(2):
            create_form.click_add_row()
        create_form.set_row_start_date(VALID_START_DATE, row_index=0)
        create_form.set_row_interest_rate("5", row_index=0)
        create_form.set_row_start_date(VALID_START_DATE, row_index=1)
        create_form.set_row_interest_rate("6", row_index=1)
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()

    def test_verify_that_schedule_start_dates_must_be_in_ascending_order(self, create_form, steps):
        """CREATE SL 16 / VALIDATION SL 5 — A later row cannot pre-date an earlier one."""
        steps.append("Added a second row dated before the first")
        create_form.fill_name(_unique("AutoLIRDesc"))
        create_form.select_type("Revolving")
        for _ in range(2):
            create_form.click_add_row()
        create_form.set_row_start_date("09/01/2026", row_index=0)
        create_form.set_row_interest_rate("5", row_index=0)
        create_form.set_row_start_date("08/01/2026", row_index=1)
        create_form.set_row_interest_rate("6", row_index=1)
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()


class TestNotesValidation:
    """Checklist CREATE SL 32-35 and UPDATE SL 40-43."""

    def test_verify_that_the_notes_field_is_optional(
        self, loan_interest_rate_listing_page, steps
    ):
        """CREATE SL 32-33 — Notes may be left empty."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRNoNotes")
        steps.append("Saved a rate with Notes left empty")
        _fill_minimum(rp, name)
        rp.save()
        try:
            rp.wait_for_view_page()
        finally:
            _cleanup(listing, rp, name)

    def test_verify_that_notes_accept_1000_characters(
        self, loan_interest_rate_listing_page, steps
    ):
        """CREATE SL 34 / UPDATE SL 42 — Notes accepts 1000 characters."""
        listing = loan_interest_rate_listing_page
        listing.click_create()
        rp = LoanInterestRatePage(listing.page)
        name = _unique("AutoLIRNotes")
        steps.append(f"Entered a {NOTES_MAX}-character note")
        _fill_minimum(rp, name)
        rp.set_row_notes("X" * NOTES_MAX)
        rp.save()
        try:
            rp.wait_for_view_page()
        finally:
            _cleanup(listing, rp, name)

    @pytest.mark.xfail(
        reason="CREATE SL 35 requires a 1001-character note to be rejected, but the "
               "record saved successfully (confirmed live 2026-08-17). Either the cap "
               "is not enforced on create or it is higher than the documented 1000.",
        strict=False,
    )
    def test_verify_that_notes_longer_than_1000_characters_are_rejected(self, create_form, steps):
        """CREATE SL 35 / UPDATE SL 43 — Notes over 1000 characters is rejected."""
        steps.append(f"Entered a {NOTES_MAX + 1}-character note")
        _fill_minimum(create_form, _unique("AutoLIRNotesLong"))
        create_form.set_row_notes("X" * (NOTES_MAX + 1))
        create_form.save()
        create_form.page.wait_for_timeout(2_500)
        assert "Create" in create_form.get_page_title() or create_form.error_banner_text()
