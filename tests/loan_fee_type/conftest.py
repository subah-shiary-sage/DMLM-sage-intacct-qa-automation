"""
conftest.py — Loan Fee Type-specific fixtures.

Session-wide fixtures (authenticated_page, steps, bug-report reporting) live in
the parent tests/conftest.py and are automatically available here.

Field values verified live against release www-p303 / SNL_release_monthly /
LME entity on 2026-08-12.
"""

import uuid

import pytest

# Picker queries verified live. GL account is mandatory on create; Item is not.
GL_ACCOUNT_QUERY = "1322"
ITEM_QUERY = "A001"


@pytest.fixture()
def unique_fee_type_name() -> str:
    """Unique name that cannot collide with an existing record."""
    return f"AutoFeeType_{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture()
def fee_type_listing_page(authenticated_page):
    """Navigate to the Loan fee type list and return the listing POM."""
    from pages.loan_fee_type.listing_page import LoanFeeTypeListingPage

    listing = LoanFeeTypeListingPage(authenticated_page)
    listing.navigate_to_list()
    return listing


@pytest.fixture()
def create_form(fee_type_listing_page, steps):
    """Open the Create form and return a ready-to-use page object."""
    from pages.loan_fee_type.fee_type_page import LoanFeeTypePage

    fee_type_listing_page.click_create()
    steps.append("Opened the Loan fee type Create form")
    return LoanFeeTypePage(fee_type_listing_page.page)


def fill_minimum_valid_fee_type(fee_type_page, name: str):
    """Fill the only two fields required to save: Name and GL account."""
    fee_type_page.fill_name(name)
    fee_type_page.set_gl_account(GL_ACCOUNT_QUERY)


def delete_if_present(listing, fee_type_page, name: str) -> None:
    """Best-effort cleanup — silent if the test already deleted the record."""
    try:
        listing.navigate_to_list()
        listing.search_by_name(name)
        if listing.is_record_visible(name):
            listing.open_record_by_name(name)
            fee_type_page.click_delete()
            fee_type_page.confirm_delete()
            listing.wait_for_list_page()
    except Exception:
        pass


@pytest.fixture()
def created_fee_type(fee_type_listing_page, unique_fee_type_name):
    """
    Create a minimum-valid fee type, leave the browser on the list, and yield
    its name. Best-effort delete afterwards.
    """
    from pages.loan_fee_type.fee_type_page import LoanFeeTypePage

    listing = fee_type_listing_page
    listing.click_create()
    ft = LoanFeeTypePage(listing.page)
    fill_minimum_valid_fee_type(ft, unique_fee_type_name)
    ft.save()
    ft.wait_for_view_page()
    listing.navigate_to_list()

    yield unique_fee_type_name

    delete_if_present(listing, ft, unique_fee_type_name)


@pytest.fixture()
def fee_type_for_delete(fee_type_listing_page, unique_fee_type_name):
    """Create a fee type for delete tests; the test itself removes it."""
    from pages.loan_fee_type.fee_type_page import LoanFeeTypePage

    listing = fee_type_listing_page
    listing.click_create()
    ft = LoanFeeTypePage(listing.page)
    fill_minimum_valid_fee_type(ft, unique_fee_type_name)
    ft.save()
    ft.wait_for_view_page()
    listing.navigate_to_list()
    return unique_fee_type_name
