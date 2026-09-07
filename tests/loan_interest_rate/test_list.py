"""
test_list.py
=======================
Playwright / pytest tests for the Loan Interest Rate **list** page
(Lending Management → Setup → Loan interest rates).

Test IDs: TC-LIR-001 – TC-LIR-010
Selectors/flows verified against live DOM 2026-07-16.
"""

import re

import pytest
from playwright.sync_api import expect

from pages.loan_interest_rate.listing_page import LoanInterestRateListingPage
from pages.loan_interest_rate.rate_page import LoanInterestRatePage


class TestLoanInterestRateList:

    def test_verify_that_the_list_page_loads_with_the_loan_interest_rates_heading(self, loan_interest_rate_listing_page, steps):
        """TC-LIR-001 — The list page loads with heading 'Loan interest rates'."""
        steps.append("Navigated to Lending Management > Setup > Loan interest rates")
        listing = loan_interest_rate_listing_page
        expect(
            listing.frame.get_by_role("heading", name=listing.LIST_HEADING)
        ).to_be_visible()

    def test_verify_that_the_create_action_is_available_on_the_list_toolbar(self, loan_interest_rate_listing_page, steps):
        """TC-LIR-002 — The Create action is available on the toolbar."""
        steps.append("Opened Loan interest rates list page")
        assert loan_interest_rate_listing_page.is_create_visible()

    def test_verify_that_the_grid_displays_name_loan_type_and_status_columns(self, loan_interest_rate_listing_page, steps):
        """TC-LIR-003 — Grid has 'Name', 'Loan type', 'Status' columns."""
        steps.append("Read column headers from the Loan interest rates grid")
        headers = " ".join(loan_interest_rate_listing_page.get_column_headers()).lower()
        assert "name" in headers
        assert "loan type" in headers
        assert "status" in headers

    def test_verify_that_the_name_filter_displays_the_contains_placeholder(self, loan_interest_rate_listing_page, steps):
        """TC-LIR-004 — Name filter shows placeholder 'Contains'."""
        steps.append("Inspected the Name column filter input")
        expect(loan_interest_rate_listing_page._name_filter()).to_have_attribute("placeholder", "Contains")

    def test_verify_that_the_loan_type_filter_is_a_dropdown(self, loan_interest_rate_listing_page, steps):
        """TC-LIR-005 — The Loan type filter column is a combobox."""
        steps.append("Located the Loan type column filter")
        combos = loan_interest_rate_listing_page.frame.get_by_role("combobox", name="Loan type")
        expect(combos.first).to_be_visible()

    def test_verify_that_the_status_filter_defaults_to_active(self, loan_interest_rate_listing_page, steps):
        """TC-LIR-006 — The Status column filter defaults to 'Active'."""
        steps.append("Checked the Status column filter default value")
        # The filter is an <input role="combobox">; its displayed value lives
        # in the value attribute, not textContent, so use to_have_value.
        status_combo = loan_interest_rate_listing_page.frame.get_by_role("combobox", name="Status").first
        expect(status_combo).to_have_value("Active")

    def test_verify_that_the_grid_displays_at_least_one_interest_rate(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-007 — The grid shows at least one record."""
        steps.append(f"Created loan interest rate '{created_loan_interest_rate}' via fixture")
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        steps.append(f"Filtered by name '{created_loan_interest_rate}'")
        assert listing.is_record_visible(created_loan_interest_rate)

    def test_verify_that_filtering_by_name_returns_the_matching_interest_rate(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-008 — Filtering by an existing name shows that record."""
        listing = loan_interest_rate_listing_page
        steps.append(f"Filtering list by '{created_loan_interest_rate}'")
        listing.search_by_name(created_loan_interest_rate)
        assert listing.is_record_visible(created_loan_interest_rate), (
            f"'{created_loan_interest_rate}' should be visible after filtering"
        )

    def test_verify_that_bulk_delete_is_disabled_when_no_row_is_selected(self, loan_interest_rate_listing_page, steps):
        """TC-LIR-009 — Toolbar Delete is disabled when no row is selected."""
        steps.append("Opened list page with no rows selected")
        expect(loan_interest_rate_listing_page.bulk_delete_button()).to_be_disabled()

    def test_verify_that_selecting_a_row_enables_bulk_delete(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """TC-LIR-010 — Selecting a row enables the toolbar Delete."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        steps.append(f"Filtered to '{created_loan_interest_rate}' then selected its row checkbox")
        listing.select_first_row()
        expect(listing.bulk_delete_button()).to_be_enabled()

    def test_verify_that_select_all_selects_the_visible_rows_and_enables_bulk_delete(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """LISTER UI — Select all applies to the visible result set."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        steps.append("Selected every visible lister row")
        listing.select_all_rows()
        expect(listing.bulk_delete_button()).to_be_enabled()

    def test_verify_that_the_lister_footer_displays_the_item_count(
        self, loan_interest_rate_listing_page, steps
    ):
        """LISTER UI — The pagination footer displays an item count."""
        steps.append("Read the lister footer")
        assert "item" in loan_interest_rate_listing_page.get_items_count_text().lower()

    def test_verify_that_the_manage_view_button_is_present(
        self, loan_interest_rate_listing_page, steps
    ):
        """LISTER UI — Manage view is available on the toolbar."""
        steps.append("Checked the toolbar for Manage view")
        expect(
            loan_interest_rate_listing_page.frame.get_by_role("button", name="Manage view")
        ).to_be_visible()

    def test_verify_that_the_view_filters_button_is_present(
        self, loan_interest_rate_listing_page, steps
    ):
        """LISTER UI — View filters is available on the toolbar."""
        steps.append("Checked the toolbar for View filters")
        expect(
            loan_interest_rate_listing_page.frame.get_by_role("button", name="View filters")
        ).to_be_visible()

    def test_verify_that_list_view_and_split_view_buttons_are_present(
        self, loan_interest_rate_listing_page, steps
    ):
        """LISTER UI — List view and Split view controls are available."""
        steps.append("Checked the toolbar for both view modes")
        frame = loan_interest_rate_listing_page.frame
        expect(frame.get_by_role("button", name="List view")).to_be_visible()
        expect(frame.get_by_role("button", name="Split view")).to_be_visible()

    def test_verify_that_the_configure_column_control_is_present(
        self, loan_interest_rate_listing_page, steps
    ):
        """LISTER UI — The user can open column configuration."""
        steps.append("Checked the toolbar for Configure column")
        expect(
            loan_interest_rate_listing_page.frame.get_by_role(
                "button", name=re.compile("Configure column", re.IGNORECASE)
            )
        ).to_be_visible()

    @pytest.mark.xfail(
        reason="The current lister family can expose BULK_SELECTED as a raw column key.",
        strict=False,
    )
    def test_verify_that_lister_column_names_do_not_contain_raw_resource_keys(
        self, loan_interest_rate_listing_page, steps
    ):
        """LISTER UI — Column names are readable and localised."""
        steps.append("Checked all lister headers for raw resource keys")
        assert not loan_interest_rate_listing_page.has_raw_column_keys()

    def test_verify_that_clicking_a_rate_name_opens_its_detail_page(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — A linked Name opens the selected record."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        steps.append(f"Opened {created_loan_interest_rate} from its Name link")
        listing.open_record_by_name(created_loan_interest_rate)
        expect(listing.frame.locator("h1").filter(has_text="Loan interest rates:")).to_be_visible()

    def test_verify_that_the_loan_type_filter_can_show_revolving_records(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — Loan type filtering retains matching Revolving records."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        steps.append("Applied the Revolving Loan type filter")
        listing.filter_by_loan_type("Revolving")
        assert listing.is_record_visible(created_loan_interest_rate)

    def test_verify_that_the_status_filter_can_show_active_records(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — Status filtering retains matching Active records."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        steps.append("Applied the Active Status filter")
        listing.filter_by_status("Active")
        assert listing.is_record_visible(created_loan_interest_rate)

    def test_verify_that_clearing_the_name_filter_removes_the_entered_text(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — Clearing Name removes the active search value."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        listing.clear_search()
        steps.append("Cleared the Name filter")
        expect(listing._name_filter()).to_have_value("")

    def test_verify_that_a_filtered_record_is_rendered_under_the_expected_columns(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — Record data renders beneath Name, Loan type, and Status."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        steps.append("Compared the visible record with the lister headers")
        assert created_loan_interest_rate in listing.row_names()
        headers = set(listing.get_column_headers())
        assert {"Name", "Loan type", "Status"} <= headers

    def test_verify_that_the_loan_type_filter_can_show_non_revolving_records(
        self, interest_rate_scenario_factory, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — Loan type filtering supports Non-revolving records."""
        scenario = interest_rate_scenario_factory.create_rate(rate_type="Non-revolving")
        listing = loan_interest_rate_listing_page
        listing.navigate_to_list()
        listing.search_by_name(scenario["name"])
        listing.filter_by_loan_type("Non-revolving")
        steps.append("Filtered the lister to Non-revolving")
        assert listing.is_record_visible(scenario["name"])

    def test_verify_that_the_status_filter_can_show_inactive_records(
        self, interest_rate_scenario_factory, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — Status filtering supports Inactive records."""
        scenario = interest_rate_scenario_factory.create_rate()
        rp = interest_rate_scenario_factory.open_rate_edit(scenario)
        rp.set_status("Inactive")
        rp.save()
        rp.wait_for_view_page()
        listing = loan_interest_rate_listing_page
        listing.navigate_to_list()
        listing.filter_by_status("Inactive")
        listing.search_by_name(scenario["name"])
        steps.append("Filtered the lister to Inactive")
        assert listing.is_record_visible(scenario["name"])

    def test_verify_that_bulk_delete_removes_a_selected_unassigned_rate(
        self, created_loan_interest_rate, loan_interest_rate_listing_page, steps
    ):
        """LISTER function — Bulk Delete removes a selected unassigned rate."""
        listing = loan_interest_rate_listing_page
        listing.search_by_name(created_loan_interest_rate)
        listing.select_first_row()
        steps.append("Selected the rate and used lister Bulk Delete")
        listing.bulk_delete_button().click()
        listing.confirm_delete()
        listing.wait_for_list_page()
        listing.search_by_name(created_loan_interest_rate)
        assert not listing.is_record_visible(created_loan_interest_rate)
