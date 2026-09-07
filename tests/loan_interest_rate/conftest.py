"""
conftest.py — Loan Interest Rate-specific fixtures.

Session-wide fixtures (authenticated_page, steps, bug-report reporting) live
in the parent tests/conftest.py and are automatically available here.
"""

import datetime
import uuid

import pytest


ASSIGNED_ORIGINATION_DATE = "12/01/2026"
REVOLVING_LOAN_TYPE = "Loan Type 01"
ACCOUNT_CATEGORY = "Loan Category 01"
CUSTOMER_QUERY = "Power Aerospace"
CUSTOMER_OPTION = "1--Power Aerospace Materials"
VENDOR_QUERY = "V0001"
VENDOR_OPTION = "V0001--Visa Card Vendor"
LOCATION_QUERY = "LME"


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: test data generators
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def unique_loan_interest_rate_name() -> str:
    """Unique Loan interest rate name guaranteed not to collide with existing records."""
    return f"AutoInterestRate_{uuid.uuid4().hex[:8].upper()}"


def _first_of_next_month() -> str:
    """
    A Loan interest rate schedule row's Start date must be the first day of a
    month (server-side validation — see TEST_CASES_Loan_Interest_Rate.xlsx
    TC-LIR-021). Computed relative to today rather than hardcoded so this
    fixture data stays valid indefinitely.
    """
    today = datetime.date.today()
    year = today.year + (1 if today.month == 12 else 0)
    month = 1 if today.month == 12 else today.month + 1
    return f"{month:02d}/01/{year}"


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: navigation fixture
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def loan_interest_rate_listing_page(authenticated_page):
    """Navigate to the Loan Interest Rate list and return the listing POM."""
    from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
    listing = LoanInterestRateListingPage(authenticated_page)
    listing.navigate_to_list()
    return listing


def _fill_minimum_valid_loan_interest_rate(rate_page, name: str):
    """
    Fill every field required to save a Loan Interest Rate: Name, Type, and
    one schedule row with a valid (first-of-month) Start date and an
    Interest rate — both server-side required (TC-LIR-020/021).
    """
    rp = rate_page
    rp.fill_name(name)
    rp.select_type("Revolving")
    rp.click_add_row()
    rp.set_row_start_date(_first_of_next_month())
    rp.set_row_interest_rate("5.5")


class InterestRateScenarioFactory:
    """Create isolated rates and optional assigned loans for rule tests."""

    def __init__(self, page):
        self.page = page
        self.rate_names: list[str] = []
        self.loan_names: list[str] = []

    def create_rate(
        self,
        rate_type: str = "Revolving",
        dates: tuple[str, ...] = ("09/01/2026",),
    ) -> dict:
        from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
        from pages.loan_interest_rate.rate_page import LoanInterestRatePage

        listing = LoanInterestRateListingPage(self.page)
        listing.navigate_to_list()
        listing.click_create()
        rate_page = LoanInterestRatePage(self.page)
        name = f"AutoLIRRule_{uuid.uuid4().hex[:8].upper()}"
        rate_page.fill_name(name)
        rate_page.select_type(rate_type)
        for _ in dates:
            rate_page.click_add_row()
        for index, date in enumerate(dates):
            rate_page.set_row_start_date(date, index)
            rate_page.set_row_interest_rate(str(5 + index), index)
            rate_page.set_row_notes(f"Schedule entry {index + 1}", index)
        rate_page.save()
        rate_page.wait_for_view_page()
        self.rate_names.append(name)
        return {
            "name": name,
            "type": rate_type,
            "dates": list(dates),
            "loan_name": None,
        }

    def assign_to_revolving_loan(
        self,
        scenario: dict,
        origination_date: str = ASSIGNED_ORIGINATION_DATE,
    ) -> dict:
        """Create a transaction-free revolving loan using the scenario rate."""
        loan_page, loan_name = self.open_revolving_loan_create_using_rate(
            scenario, origination_date
        )
        loan_page.save()
        try:
            loan_page.wait_for_view_page()
        except Exception as error:
            alerts = loan_page.frame.get_by_role("alert")
            message = alerts.first.inner_text() if alerts.count() else ""
            title = loan_page.get_page_title()
            raise AssertionError(
                f"temporary assigned loan did not save; title={title!r}, error={message!r}"
            ) from error
        self.loan_names.append(loan_name)
        scenario["loan_name"] = loan_name
        scenario["origination_date"] = origination_date
        return scenario

    def open_revolving_loan_create_using_rate(
        self,
        scenario: dict,
        origination_date: str = ASSIGNED_ORIGINATION_DATE,
        select_rate_before_origination: bool = False,
    ):
        """Fill, but do not save, a revolving loan that selects the scenario rate."""
        from pages.loan_account.account_page import LoanAccountPage
        from pages.loan_account.listing_page import LoanAccountListingPage

        listing = LoanAccountListingPage(self.page)
        listing.navigate_to_list()
        listing.click_create()
        loan_page = LoanAccountPage(self.page)
        loan_name = f"AutoLIRLoan_{uuid.uuid4().hex[:8].upper()}"
        loan_page.set_account_category(ACCOUNT_CATEGORY)
        self.page.wait_for_timeout(500)
        if not loan_page.is_account_number_readonly():
            loan_page.fill_account_number(f"LIR{uuid.uuid4().hex[:7].upper()}")
        loan_page.fill_account_name(loan_name)
        loan_page.set_customer(CUSTOMER_QUERY, CUSTOMER_OPTION)
        loan_page.set_vendor(VENDOR_QUERY, VENDOR_OPTION)
        loan_page.fill_amount("1000")
        loan_page.set_loan_type(REVOLVING_LOAN_TYPE)
        if select_rate_before_origination:
            loan_page.set_interest_rate(scenario["name"])
            loan_page.set_origination_date(origination_date)
        else:
            loan_page.set_origination_date(origination_date)
            loan_page.set_interest_rate(scenario["name"])
        if loan_page.has_create_amortization_checkbox():
            loan_page.toggle_create_amortization_schedule()
            self.page.wait_for_timeout(600)
        if loan_page.frame.get_by_role("textbox", name="Term in months").count():
            loan_page.fill_term_in_months("12")
        if loan_page.frame.get_by_role("textbox", name="First payment date").count():
            loan_page.set_first_payment_date("01/01/2027")
        loan_page.set_location(LOCATION_QUERY)
        return loan_page, loan_name

    def open_rate_edit(self, scenario: dict):
        from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
        from pages.loan_interest_rate.rate_page import LoanInterestRatePage

        listing = LoanInterestRateListingPage(self.page)
        listing.navigate_to_list()
        listing.search_by_name(scenario["name"])
        listing.open_record_by_name(scenario["name"])
        rate_page = LoanInterestRatePage(self.page)
        rate_page.wait_for_view_page()
        rate_page.click_edit()
        return rate_page

    def reopen_rate_view(self, scenario: dict):
        from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
        from pages.loan_interest_rate.rate_page import LoanInterestRatePage

        listing = LoanInterestRateListingPage(self.page)
        listing.navigate_to_list()
        listing.search_by_name(scenario["name"])
        listing.open_record_by_name(scenario["name"])
        rate_page = LoanInterestRatePage(self.page)
        rate_page.wait_for_view_page()
        return rate_page

    def cleanup(self):
        from pages.loan_account.account_page import LoanAccountPage
        from pages.loan_account.listing_page import LoanAccountListingPage
        from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
        from pages.loan_interest_rate.rate_page import LoanInterestRatePage

        loan_listing = LoanAccountListingPage(self.page)
        loan_page = LoanAccountPage(self.page)
        for name in reversed(self.loan_names):
            try:
                loan_listing.navigate_to_list()
                loan_listing.search_by_account_name(name)
                if loan_listing.is_record_visible_by_name(name):
                    loan_listing.open_record_by_account_name(name)
                    loan_page.click_delete()
                    loan_page.confirm_delete_in_modal()
                    loan_listing.wait_for_list_page()
            except Exception:
                pass

        rate_listing = LoanInterestRateListingPage(self.page)
        rate_page = LoanInterestRatePage(self.page)
        for name in reversed(self.rate_names):
            try:
                rate_listing.navigate_to_list()
                rate_listing.search_by_name(name)
                if rate_listing.is_record_visible(name):
                    rate_listing.open_record_by_name(name)
                    rate_page.click_delete()
                    rate_page.confirm_delete_in_modal()
                    rate_listing.wait_for_list_page()
            except Exception:
                pass


@pytest.fixture()
def interest_rate_scenario_factory(authenticated_page):
    factory = InterestRateScenarioFactory(authenticated_page)
    yield factory
    factory.cleanup()


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: pre-existing Loan Interest Rate fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def created_loan_interest_rate(loan_interest_rate_listing_page, unique_loan_interest_rate_name):
    """
    Create a minimum-valid Loan Interest Rate before the test, return to the
    list, and yield its name. Best-effort delete afterwards (silent if the
    test already deleted it).
    """
    from pages.loan_interest_rate.rate_page import LoanInterestRatePage

    listing = loan_interest_rate_listing_page
    listing.click_create()
    rp = LoanInterestRatePage(listing.page)
    _fill_minimum_valid_loan_interest_rate(rp, unique_loan_interest_rate_name)
    rp.save()
    rp.wait_for_view_page()
    # The list's search index can lag record creation by a couple of
    # seconds; give it a head start before navigating back to the list.
    listing.page.wait_for_timeout(1_500)
    listing.navigate_to_list()          # leave on the list so the record is openable

    yield unique_loan_interest_rate_name

    # ── Teardown ──────────────────────────────────────────────────────────────
    try:
        listing.navigate_to_list()
        listing.search_by_name(unique_loan_interest_rate_name)
        if listing.is_record_visible(unique_loan_interest_rate_name):
            listing.open_record_by_name(unique_loan_interest_rate_name)
            rp.click_delete()
            rp.confirm_delete_in_modal()
    except Exception:
        pass  # Record was already deleted by the test — safe to ignore.


@pytest.fixture()
def loan_interest_rate_for_delete(loan_interest_rate_listing_page, unique_loan_interest_rate_name):
    """Create a Loan Interest Rate for delete tests, return to the list, return its name."""
    from pages.loan_interest_rate.rate_page import LoanInterestRatePage

    listing = loan_interest_rate_listing_page
    listing.click_create()
    rp = LoanInterestRatePage(listing.page)
    _fill_minimum_valid_loan_interest_rate(rp, unique_loan_interest_rate_name)
    rp.save()
    rp.wait_for_view_page()
    # The list's search index can lag record creation by a couple of
    # seconds; give it a head start before navigating back to the list.
    listing.page.wait_for_timeout(1_500)
    listing.navigate_to_list()          # leave on the list; the test deletes it
    return unique_loan_interest_rate_name
