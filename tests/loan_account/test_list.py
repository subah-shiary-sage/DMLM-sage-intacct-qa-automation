"""
test_list.py
=======================
Playwright / pytest tests for the Loan Account **list** page
(Lending Management → All → Loan account).

Test IDs: TC-LA-131 – TC-LA-145
Selectors/flows verified against live DOM 2026-08-17 (release www-p303,
LME entity). Sage Intacct labels the list "Loans" (heading), though the
module menu item and Create page both say "loan account" / "loan".
"""

import pytest
from playwright.sync_api import expect

from pages.loan_account.listing_page import LoanAccountListingPage
from pages.loan_account.account_page import LoanAccountPage


class TestLoanAccountList:

    def test_the_list_page_loads_with_the_heading_loans(self, loan_account_listing_page, steps):
        """TC-LA-131 — The list page loads with heading 'Loans'."""
        steps.append("Navigated to Lending Management > All > Loan account")
        listing = loan_account_listing_page
        expect(listing.frame.get_by_role("heading", name=listing.LIST_HEADING)).to_be_visible()

    def test_the_create_action_is_available_on_the_toolbar(self, loan_account_listing_page, steps):
        """TC-LA-132 — The Create action is available on the toolbar."""
        steps.append("Opened Loans list page")
        assert loan_account_listing_page.is_create_visible()

    def test_the_grid_shows_the_expected_columns(self, loan_account_listing_page, steps):
        """TC-LA-133 — Grid has Account number, Account name, Account category,
        Loan type, Customer, Vendor, State and Status columns."""
        steps.append("Read column headers from the Loans grid")
        headers = " ".join(loan_account_listing_page.get_column_headers()).lower()
        for expected in [
            "account number", "account name", "account category", "loan type",
            "customer", "vendor", "state", "status",
        ]:
            assert expected in headers, f"Missing column: {expected}"

    def test_the_account_number_filter_shows_the_contains_placeholder(self, loan_account_listing_page, steps):
        """TC-LA-134 — Account number filter shows placeholder 'Contains'."""
        steps.append("Inspected the Account number column filter input")
        expect(loan_account_listing_page._account_number_filter()).to_have_attribute("placeholder", "Contains")

    def test_the_account_name_filter_shows_the_contains_placeholder(self, loan_account_listing_page, steps):
        """TC-LA-135 — Account name filter shows placeholder 'Contains'."""
        steps.append("Inspected the Account name column filter input")
        expect(loan_account_listing_page._account_name_filter()).to_have_attribute("placeholder", "Contains")

    def test_the_grid_shows_at_least_one_record_after_creation(self, created_loan_account, loan_account_listing_page, steps):
        """TC-LA-136 — The grid shows at least one record after creation."""
        steps.append(f"Created loan account '{created_loan_account}' via fixture")
        listing = loan_account_listing_page
        listing.search_by_account_name(created_loan_account)
        steps.append(f"Filtered by name '{created_loan_account}'")
        assert listing.is_record_visible_by_name(created_loan_account)

    def test_filtering_by_an_existing_account_name_shows_that_record(self, created_loan_account, loan_account_listing_page, steps):
        """TC-LA-137 — Filtering by an existing Account name shows that record."""
        listing = loan_account_listing_page
        steps.append(f"Filtering list by '{created_loan_account}'")
        listing.search_by_account_name(created_loan_account)
        assert listing.is_record_visible_by_name(created_loan_account), (
            f"'{created_loan_account}' should be visible after filtering"
        )

    def test_the_toolbar_delete_button_is_disabled_when_no_row_is_selected(self, loan_account_listing_page, steps):
        """TC-LA-138 — Toolbar Delete is disabled when no row is selected."""
        steps.append("Opened list page with no rows selected")
        expect(loan_account_listing_page.bulk_delete_button()).to_be_disabled()

    def test_selecting_a_row_enables_the_toolbar_delete_button(self, created_loan_account, loan_account_listing_page, steps):
        """TC-LA-139 — Selecting a row enables the toolbar Delete."""
        listing = loan_account_listing_page
        listing.search_by_account_name(created_loan_account)
        steps.append(f"Filtered to '{created_loan_account}' then selected its row checkbox")
        listing.select_first_row()
        expect(listing.bulk_delete_button()).to_be_enabled()

    def test_the_select_all_checkbox_selects_every_row_and_enables_delete(self, created_loan_account, loan_account_listing_page, steps):
        """TC-LA-140 — Select All checkbox selects all rows and enables Delete."""
        listing = loan_account_listing_page
        listing.search_by_account_name(created_loan_account)
        steps.append("Clicked the header 'Select all' checkbox")
        listing.select_all_rows()
        expect(listing.bulk_delete_button()).to_be_enabled()

    def test_the_pagination_area_shows_the_total_item_count(self, loan_account_listing_page, steps):
        """TC-LA-141 — Pagination area shows total item count."""
        steps.append("Checked footer/pagination area")
        text = loan_account_listing_page.get_items_count_text()
        assert "item" in text.lower()

    def test_the_manage_view_button_is_visible(self, loan_account_listing_page, steps):
        """TC-LA-142 — 'Manage view' button is visible."""
        steps.append("Checked toolbar for 'Manage view'")
        expect(loan_account_listing_page.frame.get_by_role("button", name="Manage view")).to_be_visible()

    def test_the_filters_button_is_visible(self, loan_account_listing_page, steps):
        """TC-LA-143 — 'Filters' button is visible."""
        steps.append("Checked toolbar for 'View filters'")
        expect(loan_account_listing_page.frame.get_by_role("button", name="View filters")).to_be_visible()

    def test_the_list_view_and_split_view_toggle_buttons_are_present(self, loan_account_listing_page, steps):
        """TC-LA-144 — List view and Split view toggle buttons are present."""
        steps.append("Checked toolbar for List view / Split view toggles")
        expect(loan_account_listing_page.frame.get_by_role("button", name="List view")).to_be_visible()
        expect(loan_account_listing_page.frame.get_by_role("button", name="Split view")).to_be_visible()

    def test_opening_a_record_from_the_list_navigates_to_its_view_page(self, created_loan_account, loan_account_listing_page, steps):
        """TC-LA-145 — Clicking a record's row navigates to its View page."""
        listing = loan_account_listing_page
        name = created_loan_account
        steps.append(f"Opened record '{name}' from the list")
        listing.open_record_by_account_name(name)
        acc = LoanAccountPage(listing.page)
        expect(acc.frame.locator("h1").filter(has_text="Loan:")).to_be_visible()
