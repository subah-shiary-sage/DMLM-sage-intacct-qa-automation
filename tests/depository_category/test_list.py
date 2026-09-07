"""
test_list.py
=================================
Playwright / pytest tests for the Depository Account Category **list** page.

Test IDs: DAC_L_001 – DAC_L_009  (new coverage, added 2026-07-15)
"""

import pytest
from playwright.sync_api import expect

from pages.depository_category.listing_page import DepositoryAccountCategoryListingPage
from pages.depository_category.category_page import DepositoryAccountCategoryPage


class TestDepositoryAccountCategoryList:

    def test_dac_l_001_list_page_loads(self, category_listing_page):
        """DAC_L_001 — The list page loads with the correct heading."""
        listing = category_listing_page
        expect(
            listing.frame.get_by_role("heading", name=listing.LIST_HEADING)
        ).to_be_visible()

    def test_dac_l_002_grid_columns_present(self, category_listing_page):
        """DAC_L_002 — Name, Document sequence and Status columns are present."""
        headers = " ".join(category_listing_page.get_column_headers()).lower()
        assert "name" in headers
        assert "document sequence" in headers
        assert "status" in headers

    def test_dac_l_003_create_button_present(self, category_listing_page):
        """DAC_L_003 — The Create action is available on the toolbar."""
        assert category_listing_page.is_create_visible()

    def test_dac_l_004_name_filter_returns_matching_record(self, created_category, category_listing_page):
        """DAC_L_004 — Filtering by an existing Name shows that record."""
        listing = category_listing_page
        listing.search_by_name(created_category)
        assert listing.is_record_visible(created_category), (
            f"'{created_category}' should be visible after filtering"
        )

    def test_dac_l_005_status_filter_defaults_to_active(self, category_listing_page):
        """DAC_L_005 — The Status column filter defaults to 'Active'."""
        status_combo = category_listing_page.frame.get_by_role("combobox", name="Status").first
        expect(status_combo).to_contain_text("Active")

    def test_dac_l_006_bulk_delete_disabled_by_default(self, category_listing_page):
        """DAC_L_006 — The toolbar Delete is disabled when no row is selected."""
        expect(category_listing_page.bulk_delete_button()).to_be_disabled()

    def test_dac_l_007_bulk_delete_enables_after_selecting_row(self, created_category, category_listing_page):
        """DAC_L_007 — Selecting a row enables the toolbar Delete."""
        listing = category_listing_page
        listing.search_by_name(created_category)
        listing.select_first_row()
        expect(listing.bulk_delete_button()).to_be_enabled()

    def test_dac_l_008_row_exposes_actions(self, created_category, category_listing_page):
        """DAC_L_008 — A data row exposes a 'More actions' control."""
        listing = category_listing_page
        listing.search_by_name(created_category)
        assert listing.first_row_has_actions()

    def test_dac_l_009_open_record_from_list(self, created_category, category_listing_page):
        """DAC_L_009 — Clicking a record name opens its View page."""
        listing = category_listing_page
        listing.search_by_name(created_category)
        listing.open_record_by_name(created_category)
        cat = DepositoryAccountCategoryPage(listing.page)
        expect(cat.frame.locator("h1").filter(has_text="Depository account category:")).to_be_visible()
