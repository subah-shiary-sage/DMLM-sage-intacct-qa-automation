"""
conftest.py — Loan Account-specific fixtures.

Session-wide fixtures (authenticated_page, steps, bug-report reporting) live
in the parent tests/conftest.py and are automatically available here.
"""

import uuid

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: test data generators
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def unique_account_name() -> str:
    """Unique Account name guaranteed not to collide with existing records."""
    return f"AutoLoanAcct_{uuid.uuid4().hex[:8].upper()}"


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: navigation fixture
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def loan_account_listing_page(authenticated_page):
    """Navigate to the Loan account list and return the listing POM."""
    from pages.loan_account.listing_page import LoanAccountListingPage
    listing = LoanAccountListingPage(authenticated_page)
    listing.navigate_to_list()
    return listing


# Values verified live against the LME entity on 2026-08-17 — see
# TEST_CASES_Loan_Account.md for the full picker-option inventory.
# "Loan Category 01" has NO document sequence, so Account number stays an
# editable, server-required text field — this is deliberately the category
# used everywhere below so create/edit flows exercise the same field set.
ACCOUNT_CATEGORY   = "Loan Category 01"
CUSTOMER           = "Power Aerospace"
CUSTOMER_EXACT     = "1--Power Aerospace Materials"
VENDOR              = "V0001"
VENDOR_EXACT        = "V0001--Visa Card Vendor"
LOCATION            = "LME"
# Non-revolving loan type: skips the Revolving "Create amortization
# schedule" checkbox path entirely, which is a confirmed-broken save on this
# environment (raw client exceptions — see pages/loan_account/account_page.py
# docstring). Non-revolving is the reliable, live-verified create path.
LOAN_TYPE_NON_REVOLVING = "Compound_Amortized"
INTEREST_RATE_QUERY     = "a"
ORIGINATION_DATE        = "08/17/2026"
FIRST_PAYMENT_DATE      = "09/01/2026"
TERM_IN_MONTHS          = "12"
AMOUNT                  = "1000"


def _fill_minimum_valid_loan_account(account_page, name: str):
    """
    Fill every field required to save a Loan account via the reliable
    Non-revolving create path: Account category (no doc sequence, so
    Account number needs a manual value), Account name, Customer, Vendor,
    Amount, Loan type, Loan origination date, Interest rate, Term in
    months, First payment date, Location. Verified end-to-end live
    2026-08-17 (see pages/loan_account/account_page.py module docstring).
    """
    lap = account_page
    lap.set_account_category(ACCOUNT_CATEGORY)
    lap.page.wait_for_timeout(500)
    if not lap.is_account_number_readonly():
        lap.fill_account_number(f"ACCT{uuid.uuid4().hex[:6].upper()}")
        lap.page.wait_for_timeout(500)
    lap.fill_account_name(name)
    lap.set_customer(CUSTOMER, CUSTOMER_EXACT)
    lap.set_vendor(VENDOR, VENDOR_EXACT)
    lap.fill_amount(AMOUNT)
    lap.set_loan_type(LOAN_TYPE_NON_REVOLVING)
    lap.set_origination_date(ORIGINATION_DATE)
    lap.set_interest_rate(INTEREST_RATE_QUERY)
    lap.fill_term_in_months(TERM_IN_MONTHS)
    lap.set_first_payment_date(FIRST_PAYMENT_DATE)
    lap.set_location(LOCATION)


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: pre-existing Loan Account fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def created_loan_account(loan_account_listing_page, unique_account_name):
    """
    Create a minimum-valid Loan account before the test, return to the list,
    and yield its name. Best-effort delete afterwards (silent if the test
    already deleted it).
    """
    from pages.loan_account.account_page import LoanAccountPage

    listing = loan_account_listing_page
    listing.click_create()
    lap = LoanAccountPage(listing.page)
    _fill_minimum_valid_loan_account(lap, unique_account_name)
    lap.save()
    lap.wait_for_view_page()
    listing.navigate_to_list()          # leave on the list so the record is openable

    yield unique_account_name

    # ── Teardown ──────────────────────────────────────────────────────────────
    try:
        listing.navigate_to_list()
        listing.search_by_account_name(unique_account_name)
        if listing.is_record_visible_by_name(unique_account_name):
            listing.open_record_by_account_name(unique_account_name)
            lap.click_delete()
            lap.confirm_delete_in_modal()
    except Exception:
        pass  # Record was already deleted by the test — safe to ignore.


@pytest.fixture()
def loan_account_for_delete(loan_account_listing_page, unique_account_name):
    """Create a Loan account for delete tests, return to the list, return its name."""
    from pages.loan_account.account_page import LoanAccountPage

    listing = loan_account_listing_page
    listing.click_create()
    lap = LoanAccountPage(listing.page)
    _fill_minimum_valid_loan_account(lap, unique_account_name)
    lap.save()
    lap.wait_for_view_page()
    listing.navigate_to_list()          # leave on the list; the test deletes it
    return unique_account_name
