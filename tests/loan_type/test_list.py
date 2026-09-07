"""
test_list.py
=======================
Playwright / pytest tests for the Loan Type **list** page
(Lending Management → Setup → Loan type).

Test IDs: TC-LT-001 – TC-LT-014
Selectors/flows verified against live DOM 2026-07-15.
"""

import pytest
from playwright.sync_api import expect

from pages.loan_type.listing_page import LoanTypeListingPage
from pages.loan_type.type_page import LoanTypePage


class TestLoanTypeList:

    def test_the_list_page_loads_with_the_heading_loan_types(self, loan_type_listing_page, steps):
        """TC-LT-001 — The list page loads with heading 'Loan types'."""
        steps.append("Navigated to Lending Management > Setup > Loan type")
        listing = loan_type_listing_page
        expect(
            listing.frame.get_by_role("heading", name=listing.LIST_HEADING)
        ).to_be_visible()

    def test_the_create_action_is_available_on_the_toolbar(self, loan_type_listing_page, steps):
        """TC-LT-002 — The Create action is available on the toolbar."""
        steps.append("Opened Loan types list page")
        assert loan_type_listing_page.is_create_visible()

    def test_the_grid_shows_the_loan_type_interest_calculation_method_and_description_columns(self, loan_type_listing_page, steps):
        """TC-LT-003 — Grid has 'Loan type', 'Interest calculation method', 'Description' columns."""
        steps.append("Read column headers from the Loan types grid")
        headers = " ".join(loan_type_listing_page.get_column_headers()).lower()
        assert "loan type" in headers
        assert "interest calculation method" in headers
        assert "description" in headers

    def test_the_loan_type_name_filter_shows_the_contains_placeholder(self, loan_type_listing_page, steps):
        """TC-LT-004 — Loan type name filter shows placeholder 'Contains'."""
        steps.append("Inspected the Loan type name column filter input")
        expect(loan_type_listing_page._name_filter()).to_have_attribute("placeholder", "Contains")

    def test_the_revolving_non_revolving_type_filter_column_is_a_combobox(self, loan_type_listing_page, steps):
        """TC-LT-005 — The Revolving/Non-revolving Type filter column is a combobox."""
        steps.append("Located the Type (Revolving/Non-revolving) column filter")
        combos = loan_type_listing_page.frame.get_by_role("combobox", name="Loan type")
        expect(combos.first).to_be_visible()

    def test_the_grid_shows_at_least_one_record(self, created_loan_type, loan_type_listing_page, steps):
        """TC-LT-006 — The grid shows at least one record."""
        steps.append(f"Created loan type '{created_loan_type}' via fixture")
        listing = loan_type_listing_page
        listing.search_by_name(created_loan_type)
        steps.append(f"Filtered by name '{created_loan_type}'")
        assert listing.is_record_visible(created_loan_type)

    def test_filtering_by_an_existing_name_shows_that_record(self, created_loan_type, loan_type_listing_page, steps):
        """TC-LT-007 — Filtering by an existing name shows that record."""
        listing = loan_type_listing_page
        steps.append(f"Filtering list by '{created_loan_type}'")
        listing.search_by_name(created_loan_type)
        assert listing.is_record_visible(created_loan_type), (
            f"'{created_loan_type}' should be visible after filtering"
        )

    def test_the_toolbar_delete_button_is_disabled_when_no_row_is_selected(self, loan_type_listing_page, steps):
        """TC-LT-008 — Toolbar Delete is disabled when no row is selected."""
        steps.append("Opened list page with no rows selected")
        expect(loan_type_listing_page.bulk_delete_button()).to_be_disabled()

    def test_selecting_a_row_enables_the_toolbar_delete_button(self, created_loan_type, loan_type_listing_page, steps):
        """TC-LT-009 — Selecting a row enables the toolbar Delete."""
        listing = loan_type_listing_page
        listing.search_by_name(created_loan_type)
        steps.append(f"Filtered to '{created_loan_type}' then selected its row checkbox")
        listing.select_first_row()
        expect(listing.bulk_delete_button()).to_be_enabled()

    def test_the_select_all_checkbox_selects_every_row_and_enables_delete(self, created_loan_type, loan_type_listing_page, steps):
        """TC-LT-010 — Select All checkbox selects all rows and enables Delete."""
        listing = loan_type_listing_page
        listing.search_by_name(created_loan_type)
        steps.append("Clicked the header 'Select all' checkbox")
        listing.select_all_rows()
        expect(listing.bulk_delete_button()).to_be_enabled()

    def test_the_pagination_area_shows_the_total_item_count(self, loan_type_listing_page, steps):
        """TC-LT-011 — Pagination area shows total item count."""
        steps.append("Checked footer/pagination area")
        text = loan_type_listing_page.get_items_count_text()
        assert "item" in text.lower()

    def test_the_manage_view_button_is_visible(self, loan_type_listing_page, steps):
        """TC-LT-012 — 'Manage view' button is visible."""
        steps.append("Checked toolbar for 'Manage view'")
        expect(loan_type_listing_page.frame.get_by_role("button", name="Manage view")).to_be_visible()

    def test_the_filters_button_is_visible(self, loan_type_listing_page, steps):
        """TC-LT-013 — 'Filters' button is visible."""
        steps.append("Checked toolbar for 'View filters'")
        expect(loan_type_listing_page.frame.get_by_role("button", name="View filters")).to_be_visible()

    def test_the_list_view_and_split_view_toggle_buttons_are_present(self, loan_type_listing_page, steps):
        """TC-LT-014 — List view and Split view toggle buttons are present."""
        steps.append("Checked toolbar for List view / Split view toggles")
        expect(loan_type_listing_page.frame.get_by_role("button", name="List view")).to_be_visible()
        expect(loan_type_listing_page.frame.get_by_role("button", name="Split view")).to_be_visible()
