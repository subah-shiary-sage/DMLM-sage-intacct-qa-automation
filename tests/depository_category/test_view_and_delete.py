"""
test_view_and_delete.py
=============================================
Playwright / pytest tests for the VIEW and DELETE lifecycle stages of the
Depository Account Category module.

Test IDs: DAC_VD_001 – DAC_VD_015
Selectors/flows verified against live DOM 2026-07-15.
  * View heading  : "Depository account category: <ID>--<Name>"
  * Three-dot menu: only "View audit trail" (no "Object Definition" in this env)
  * Delete modal  : "Delete depository account category"
"""

import pytest
from playwright.sync_api import expect

from pages.depository_category.listing_page import DepositoryAccountCategoryListingPage
from pages.depository_category.category_page import DepositoryAccountCategoryPage


@pytest.fixture()
def view_page(created_category, category_listing_page):
    """Open the View page for a pre-created category.  Returns (page_obj, name)."""
    listing: DepositoryAccountCategoryListingPage = category_listing_page
    name: str = created_category
    listing.navigate_to_list()
    listing.search_by_name(name)
    listing.open_record_by_name(name)
    return DepositoryAccountCategoryPage(listing.page), name


class TestViewDepositoryAccountCategory:

    def test_dac_vd_001_view_page_title_format(self, view_page):
        """DAC_VD_001 — View heading is 'Depository account category: <ID>--<Name>'."""
        cat, name = view_page
        title = cat.get_page_title().lower()
        assert title.startswith("depository account category:"), f"Unexpected title: '{title}'"
        assert name.lower() in title, f"Expected '{name}' in '{title}'"

    def test_dac_vd_002_name_field_is_readonly(self, view_page):
        """DAC_VD_002 — Name renders as read-only text (no editable input)."""
        cat, name = view_page
        expect(cat.frame.get_by_text(name, exact=True).first).to_be_visible()
        assert cat.is_name_readonly(), "Name should not be an editable input on the View page"

    def test_dac_vd_003_document_sequence_field_is_readonly(self, view_page):
        """DAC_VD_003 — Document Sequence is read-only on the View page."""
        cat, _ = view_page
        editable = cat.frame.locator(
            'input[aria-label="Document sequence"]:not([readonly]):not([disabled])'
        )
        assert editable.count() == 0, "Document Sequence should not be editable on View"

    @pytest.mark.skip(reason="Drilldown only meaningful when a Document sequence is set (DAC_VD_004).")
    @pytest.mark.api
    def test_dac_vd_004_document_sequence_is_drillable(self):
        """DAC_VD_004 [API] — Document Sequence is drillable when populated."""

    def test_dac_vd_005_description_field_is_readonly(self, view_page):
        """DAC_VD_005 — Description is read-only on the View page."""
        cat, _ = view_page
        editable = cat.frame.locator(
            'input[aria-label="Description"]:not([readonly]):not([disabled]), '
            'textarea[aria-label="Description"]:not([readonly]):not([disabled])'
        )
        assert editable.count() == 0, "Description should not be editable on View"

    def test_dac_vd_006_status_field_is_readonly(self, view_page):
        """DAC_VD_006 — Status is shown as read-only text, not a dropdown."""
        cat, _ = view_page
        expect(cat.frame.locator('select[name*="STATUS"]')).to_have_count(0)
        expect(
            cat.frame.get_by_text("Active", exact=True).or_(
                cat.frame.get_by_text("Inactive", exact=True)
            ).first
        ).to_be_visible()

    def test_dac_vd_007_back_to_list_redirects_to_listing(self, view_page):
        """DAC_VD_007 — 'Back to list' returns to the listing page."""
        cat, _ = view_page
        cat.click_back_to_list()
        expect(
            cat.frame.get_by_role("heading", name="Depository account categories")
        ).to_be_visible()

    def test_dac_vd_008_three_dot_menu_contains_view_audit_trail(self, view_page):
        """DAC_VD_008 — Three-dot menu contains 'View audit trail'."""
        cat, _ = view_page
        cat.open_view_three_dot_menu()
        expect(cat.frame.get_by_role("button", name="View audit trail")).to_be_visible()

    def test_dac_vd_009_view_audit_trail_opens_audit_log(self, view_page):
        """DAC_VD_009 — Clicking 'View audit trail' opens the audit view."""
        cat, _ = view_page
        cat.click_view_audit_trail()
        expect(
            cat.frame.get_by_text("audit", exact=False).first
        ).to_be_visible(timeout=10_000)

    @pytest.mark.skip(reason="'Object Definition' is not exposed in the DMLM Depository "
                             "Account Category three-dot menu in this environment (DAC_VD_010).")
    def test_dac_vd_010_object_definition_opens_definition_page(self):
        """DAC_VD_010 — Object Definition (not available in this environment)."""


class TestDeleteDepositoryAccountCategory:

    def test_dac_vd_011_delete_button_opens_confirmation_modal(self, category_for_delete, category_listing_page):
        """DAC_VD_011 — Clicking Delete opens the confirmation modal."""
        listing = category_listing_page
        listing.open_record_by_name(category_for_delete)
        cat = DepositoryAccountCategoryPage(listing.page)
        cat.click_delete()
        # The dialog's own [role="dialog"] wrapper has a zero-size bounding box
        # (see DepositoryAccountCategoryPage._delete_dialog) so assert on the
        # heading instead — it reflects the real on-screen state. `.last` since
        # the session-scoped page can accumulate stale headings from earlier tests.
        expect(cat.frame.get_by_role("heading", name=cat.DELETE_DIALOG).last).to_be_visible()
        cat.confirm_delete_in_modal()  # cleanup

    def test_dac_vd_012_delete_modal_title_is_correct(self, category_for_delete, category_listing_page):
        """DAC_VD_012 — Modal title is 'Delete depository account category'."""
        listing = category_listing_page
        listing.open_record_by_name(category_for_delete)
        cat = DepositoryAccountCategoryPage(listing.page)
        cat.click_delete()
        assert cat.get_delete_modal_title().strip().lower() == "delete depository account category", (
            f"Unexpected modal title: '{cat.get_delete_modal_title()}'"
        )
        cat.confirm_delete_in_modal()

    def test_dac_vd_013_delete_modal_message_names_the_record(self, category_for_delete, category_listing_page):
        """DAC_VD_013 — Modal message names the record and says it will be deleted."""
        listing = category_listing_page
        listing.open_record_by_name(category_for_delete)
        cat = DepositoryAccountCategoryPage(listing.page)
        cat.click_delete()
        message = cat.get_delete_modal_message()
        assert category_for_delete in message, f"Expected '{category_for_delete}' in: '{message}'"
        assert "will be permanently deleted" in message.lower(), f"Missing deletion notice in: '{message}'"
        cat.confirm_delete_in_modal()

    def test_dac_vd_014_confirm_delete_permanently_removes_record(self, category_for_delete, category_listing_page):
        """DAC_VD_014 — Confirming Delete removes the record from the list."""
        listing: DepositoryAccountCategoryListingPage = category_listing_page
        name = category_for_delete

        listing.open_record_by_name(name)
        cat = DepositoryAccountCategoryPage(listing.page)
        cat.click_delete()
        cat.confirm_delete_in_modal()

        listing.wait_for_list_page()
        listing.search_by_name(name)
        assert not listing.is_record_visible(name), f"Record '{name}' should have been deleted"

    def test_dac_vd_015_cancel_in_modal_closes_without_deleting(self, category_for_delete, category_listing_page):
        """DAC_VD_015 — Cancel in the modal closes it without deleting."""
        listing = category_listing_page
        name = category_for_delete

        listing.open_record_by_name(name)
        cat = DepositoryAccountCategoryPage(listing.page)
        cat.click_delete()
        cat.cancel_delete_in_modal()

        # The dialog role wrapper always reports not-visible (bounding-box quirk,
        # see _delete_dialog) so that assertion would be a no-op either way;
        # assert on the heading instead to actually verify the modal closed.
        expect(cat.frame.get_by_role("heading", name=cat.DELETE_DIALOG).last).not_to_be_visible()
        expect(cat.frame.locator("h1").filter(has_text="Depository account category:")).to_be_visible()

        # Cleanup: now actually delete it.
        cat.click_delete()
        cat.confirm_delete_in_modal()
