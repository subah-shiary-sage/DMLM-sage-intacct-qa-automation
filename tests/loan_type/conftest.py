"""
conftest.py — Loan Type-specific fixtures.

Session-wide fixtures (authenticated_page, steps, bug-report reporting) live
in the parent tests/conftest.py and are automatically available here.
"""

import uuid

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: test data generators
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def unique_loan_type_name() -> str:
    """Unique Loan type name guaranteed not to collide with existing records."""
    return f"AutoLoanType_{uuid.uuid4().hex[:8].upper()}"


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: navigation fixture
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def loan_type_listing_page(authenticated_page):
    """Navigate to the Loan Type list and return the listing POM."""
    from pages.loan_type.listing_page import LoanTypeListingPage
    listing = LoanTypeListingPage(authenticated_page)
    listing.navigate_to_list()
    return listing


# Values verified live against the DMLM entity on 2026-07-15 — see
# TEST_CASES_Loan_Type.md for the full picker-option inventory.
LOAN_TYPE_ORDER_ENTRY_TXN_DEF = "Loan management invoicing"
LOAN_TYPE_PRINCIPAL_ITEM      = "p01--Loan principal item"
LOAN_TYPE_INTEREST_ITEM       = "i01--Loan interest item"


def _fill_minimum_valid_loan_type(loan_type_page, name: str):
    """
    Fill every field required to save a Revolving Loan Type: name, Type,
    Interest type, Interest calculation method (conditionally rendered after
    Type), the three Loan invoicing defaults pickers, and one Payment
    priority row (Sort order + Type are both server-side required — see
    TEST_CASES_Loan_Type.md TC-LT-057/058). Note: Non-revolving requires
    BOTH a Principal row and an Interest row (TC-LT-065) — tests exercising
    Non-revolving creation build their own row sequence rather than using
    this helper.
    """
    lt = loan_type_page
    lt.fill_name(name)
    lt.select_type("Revolving")
    lt.set_interest_type("Compound")
    lt.set_interest_calculation_method("Actual/365")
    lt.set_order_entry_transaction_definition("loan", LOAN_TYPE_ORDER_ENTRY_TXN_DEF)
    lt.set_item_for_principal_posting("loan", LOAN_TYPE_PRINCIPAL_ITEM)
    lt.set_item_for_interest_posting("interest", LOAN_TYPE_INTEREST_ITEM)
    lt.click_add_row()
    lt.set_row_sort_order("1")
    lt.set_row_type("Interest")


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: pre-existing Loan Type fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def created_loan_type(loan_type_listing_page, unique_loan_type_name):
    """
    Create a minimum-valid Loan Type before the test, return to the list, and
    yield its name. Best-effort delete afterwards (silent if the test already
    deleted it).
    """
    from pages.loan_type.type_page import LoanTypePage

    listing = loan_type_listing_page
    listing.click_create()
    lt = LoanTypePage(listing.page)
    _fill_minimum_valid_loan_type(lt, unique_loan_type_name)
    lt.save()
    lt.wait_for_view_page()
    listing.navigate_to_list()          # leave on the list so the record is openable

    yield unique_loan_type_name

    # ── Teardown ──────────────────────────────────────────────────────────────
    try:
        listing.navigate_to_list()
        listing.search_by_name(unique_loan_type_name)
        if listing.is_record_visible(unique_loan_type_name):
            listing.open_record_by_name(unique_loan_type_name)
            lt.click_delete()
            lt.confirm_delete_in_modal()
    except Exception:
        pass  # Record was already deleted by the test — safe to ignore.


@pytest.fixture()
def loan_type_for_delete(loan_type_listing_page, unique_loan_type_name):
    """Create a Loan Type for delete tests, return to the list, return its name."""
    from pages.loan_type.type_page import LoanTypePage

    listing = loan_type_listing_page
    listing.click_create()
    lt = LoanTypePage(listing.page)
    _fill_minimum_valid_loan_type(lt, unique_loan_type_name)
    lt.save()
    lt.wait_for_view_page()
    listing.navigate_to_list()          # leave on the list; the test deletes it
    return unique_loan_type_name
