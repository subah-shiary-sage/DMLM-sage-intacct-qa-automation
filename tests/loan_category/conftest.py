"""
conftest.py — Loan account category fixtures.

Session-wide fixtures (authenticated_page, steps, bug-report reporting) live in
the parent tests/conftest.py and are available automatically.

Field limits confirmed live on 2026-08-17 (release www-p303 /
SNL_release_monthly / LME entity) — these differ from the checklist wording:
  * Name        — 200 accepted, 201 rejected. No maxlength attribute.
  * Description — 500 accepted, 501 rejected. No maxlength attribute.
    The checklist's SL 13/14/60 say "1000"; the app enforces 500, so those
    rows are asserted against the real limit and the discrepancy is noted.
"""

import uuid

import pytest

NAME_MAX = 200
DESCRIPTION_MAX = 500

# Every validation error on this object leaks the internal object path.
OBJECT_PATH = "loan-management/loan-category"


@pytest.fixture()
def unique_category_name() -> str:
    return f"AutoCat_{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture()
def category_listing_page(authenticated_page):
    """Navigate to the Loan account categories list and return the listing POM."""
    from pages.loan_category.listing_page import LoanCategoryListingPage

    listing = LoanCategoryListingPage(authenticated_page)
    listing.navigate_to_list()
    return listing


@pytest.fixture()
def create_form(category_listing_page, steps):
    """Open the Create form and return a ready-to-use page object."""
    from pages.loan_category.category_page import LoanCategoryPage

    category_listing_page.click_create()
    steps.append("Opened the Loan account category Create form")
    return LoanCategoryPage(category_listing_page.page)


def delete_if_present(listing, category_page, name: str) -> None:
    """Best-effort cleanup — silent if the test already removed the record."""
    try:
        listing.navigate_to_list()
        listing.search_by_name(name)
        if listing.is_record_visible(name):
            listing.open_record_by_name(name)
            category_page.click_delete()
            category_page.confirm_delete()
            listing.wait_for_list_page()
    except Exception:
        pass


@pytest.fixture()
def created_category(category_listing_page, unique_category_name):
    """Create a minimum-valid category (Name only), yield its name, then clean up."""
    from pages.loan_category.category_page import LoanCategoryPage

    listing = category_listing_page
    listing.click_create()
    cp = LoanCategoryPage(listing.page)
    cp.fill_name(unique_category_name)
    cp.save()
    cp.wait_for_view_page()
    listing.navigate_to_list()

    yield unique_category_name

    delete_if_present(listing, cp, unique_category_name)


@pytest.fixture()
def category_for_delete(category_listing_page, unique_category_name):
    """Create a category for delete tests; the test itself removes it."""
    from pages.loan_category.category_page import LoanCategoryPage

    listing = category_listing_page
    listing.click_create()
    cp = LoanCategoryPage(listing.page)
    cp.fill_name(unique_category_name)
    cp.save()
    cp.wait_for_view_page()
    listing.navigate_to_list()
    return unique_category_name


@pytest.fixture()
def open_record(category_listing_page, created_category):
    """Open the created record's View page → (listing, page, name)."""
    from pages.loan_category.category_page import LoanCategoryPage

    listing = category_listing_page
    listing.search_by_name(created_category)
    listing.open_record_by_name(created_category)
    cp = LoanCategoryPage(listing.page)
    cp.wait_for_view_page()
    return listing, cp, created_category
