"""
test_edit.py
==================================
Playwright / pytest tests for the EDIT lifecycle stage of the
Depository Account Category module.

Test IDs: DAC_E_001 – DAC_E_009
Selectors/flows verified against live DOM 2026-07-15.
Edit heading is "Edit depository account category: <ID>--<Name>".
"""

import pytest
from playwright.sync_api import expect

from pages.depository_category.listing_page import DepositoryAccountCategoryListingPage
from pages.depository_category.category_page import DepositoryAccountCategoryPage


@pytest.fixture()
def edit_form(created_category, category_listing_page):
    """Open the Edit form for the pre-created category.  Returns (page_obj, name)."""
    listing: DepositoryAccountCategoryListingPage = category_listing_page
    original_name: str = created_category

    listing.navigate_to_list()
    listing.search_by_name(original_name)
    listing.open_record_by_name(original_name)
    cat = DepositoryAccountCategoryPage(listing.page)
    cat.click_edit()
    return cat, original_name


class TestEditDepositoryAccountCategory:

    def test_dac_e_001_edit_page_title_format(self, edit_form):
        """DAC_E_001 — Edit heading is 'Edit depository account category: <ID>--<Name>'."""
        cat, original_name = edit_form
        title = cat.get_page_title().lower()
        assert title.startswith("edit depository account category:"), f"Unexpected title: '{title}'"
        assert original_name.lower() in title, f"Expected '{original_name}' in '{title}'"

    def test_dac_e_002_name_field_is_editable(self, edit_form):
        """DAC_E_002 — Name is a writable text input in Edit mode."""
        cat, _ = edit_form
        expect(cat.frame.locator(cat.NAME_INPUT).first).to_be_editable()

    def test_dac_e_003_updating_name_with_valid_value_accepted(self, edit_form, unique_name):
        """DAC_E_003 — Updating Name with a valid value is saved."""
        cat, _ = edit_form
        new_name = unique_name + "_ED"
        cat.fill_name(new_name)
        cat.save()
        cat.wait_for_view_page()
        expect(cat.frame.locator("h1")).to_contain_text(new_name)

    def test_dac_e_004_empty_name_shows_validation_error(self, edit_form):
        """DAC_E_004 — Clearing Name and saving keeps the user in Edit mode."""
        cat, _ = edit_form
        cat.fill_name("")
        cat.save()
        cat.page.wait_for_timeout(1_500)
        expect(
            cat.frame.get_by_role("heading", name="Edit depository account category")
        ).to_be_visible()

    @pytest.mark.skip(reason="Document sequence is a picker; duplicate-key enforcement is API-level (DAC_E_005).")
    @pytest.mark.api
    def test_dac_e_005_document_sequence_rejects_duplicate_key(self):
        """DAC_E_005 [API] — Document Sequence rejects duplicate keys (server-side)."""

    def test_dac_e_006_description_editable_accepts_1000_chars(self, edit_form):
        """DAC_E_006 — Description is editable and accepts up to 1000 chars."""
        cat, _ = edit_form
        cat.fill_description("B" * 1000)
        cat.save()
        cat.wait_for_view_page()
        expect(cat.frame.locator("h1").filter(has_text="Depository account category:")).to_be_visible()

    def test_dac_e_007_status_dropdown_allows_active_inactive(self, edit_form):
        """DAC_E_007 — Status combobox switches to Inactive and persists."""
        cat, _ = edit_form
        cat.set_status("Inactive")
        cat.save()
        cat.wait_for_view_page()
        expect(cat.frame.get_by_text("Inactive").first).to_be_visible()

    def test_dac_e_008_save_button_persists_changes(self, edit_form, unique_name):
        """DAC_E_008 — Save persists changes; View heading reflects the new name."""
        cat, _ = edit_form
        updated_name = unique_name + "_SV"
        cat.fill_name(updated_name)
        cat.save()
        cat.wait_for_view_page()
        expect(cat.frame.locator("h1")).to_contain_text(updated_name)

    def test_dac_e_009_cancel_discards_changes_and_returns_to_view(self, edit_form):
        """DAC_E_009 — Cancel discards edits and returns to the View page unchanged."""
        cat, original_name = edit_form
        cat.fill_name("SHOULD_NOT_BE_SAVED")
        cat.cancel()
        cat.wait_for_view_page()
        expect(cat.frame.locator("h1")).to_contain_text(original_name)
