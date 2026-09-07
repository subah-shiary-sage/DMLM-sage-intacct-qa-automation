"""
conftest.py — Depository Account Category-specific fixtures.

Session-wide fixtures (authenticated_page, steps, bug-report reporting) live
in the parent tests/conftest.py and are automatically available here.
"""

import uuid

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: test data generators
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def unique_name() -> str:
    """Unique category Name guaranteed not to collide with existing records."""
    return f"DepAcctCat_{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture()
def unique_doc_seq() -> str:
    return f"DOCSEQ_{uuid.uuid4().hex[:6].upper()}"


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: navigation fixture
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def category_listing_page(authenticated_page):
    """Navigate to the Depository Account Category list and return the listing POM."""
    from pages.depository_category.listing_page import DepositoryAccountCategoryListingPage
    listing = DepositoryAccountCategoryListingPage(authenticated_page)
    listing.navigate_to_list()
    return listing


# ══════════════════════════════════════════════════════════════════════════════
# Function-scoped: pre-existing category fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def created_category(category_listing_page, unique_name):
    """
    Create a category before the test, return to the list, and yield its name.
    Best-effort delete afterwards (silent if the test already deleted it).
    """
    from pages.depository_category.category_page import DepositoryAccountCategoryPage

    listing = category_listing_page
    listing.click_create()
    cat = DepositoryAccountCategoryPage(listing.page)
    cat.fill_name(unique_name)
    cat.save()
    cat.wait_for_view_page()
    listing.navigate_to_list()          # leave on the list so the record is openable

    yield unique_name

    # ── Teardown ──────────────────────────────────────────────────────────────
    try:
        listing.navigate_to_list()
        listing.search_by_name(unique_name)
        if listing.is_record_visible(unique_name):
            listing.open_record_by_name(unique_name)
            cat.click_delete()
            cat.confirm_delete_in_modal()
    except Exception:
        pass  # Record was already deleted by the test — safe to ignore.


@pytest.fixture()
def category_for_delete(category_listing_page, unique_name):
    """Create a category for delete tests, return to the list, return its name."""
    from pages.depository_category.category_page import DepositoryAccountCategoryPage

    listing = category_listing_page
    listing.click_create()
    cat = DepositoryAccountCategoryPage(listing.page)
    cat.fill_name(unique_name)
    cat.save()
    cat.wait_for_view_page()
    listing.navigate_to_list()          # leave on the list; the test deletes it
    return unique_name
