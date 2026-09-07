"""
test_view_and_edit.py
=========================
Playwright / pytest tests for the VIEW and UPDATE stages of the Loan Fee Type
module.

Checklist rows: TC-LFT-025 – TC-LFT-041 ("Loan Fee Type - CRUD", SL 25-41).
Verified live against release www-p303 / SNL_release_monthly / LME entity
on 2026-08-12.

Hydration note: the view page paints "--" placeholders and fills them a moment
later, so every read goes through wait_for_view_page(), which waits for real
values. Reading earlier makes saved data look lost.

Known open defects asserted as xfail:
  * Bug #25-family — the view heading shows the record ID, not the name (SL 25).
  * Bug #31 — the edit heading exposes the raw internal object path (SL 33).
  * Bug #30 — blank/whitespace name errors leak the object path (SL 36).
"""

import pytest

from pages.loan_fee_type.fee_type_page import LoanFeeTypePage
from .conftest import GL_ACCOUNT_QUERY, ITEM_QUERY, delete_if_present

OBJECT_PATH = "loan-management/loan-fee-type"


@pytest.fixture()
def open_record(fee_type_listing_page, created_fee_type):
    """Open the created record's View page and return (listing, page, name)."""
    listing = fee_type_listing_page
    listing.search_by_name(created_fee_type)
    listing.open_record_by_name(created_fee_type)
    ft = LoanFeeTypePage(listing.page)
    ft.wait_for_view_page()
    return listing, ft, created_fee_type


class TestViewLoanFeeType:

    @pytest.mark.xfail(
        reason="The view heading shows the internal record ID instead of the name",
        strict=False,
    )
    def view_page_title_verification(self, open_record, steps):
        """TC-LFT-025 — The view title should read "Loan fee type: <Name>"."""
        _, ft, name = open_record
        steps.append("Read the view page H1")
        assert name in ft.get_page_title(), f"title was {ft.get_page_title()!r}"

    def view_page_breadcrumb_presence_verification(self, open_record, steps):
        """TC-LFT-026 — A "Loan fee types" breadcrumb is present."""
        _, ft, _ = open_record
        steps.append("Looked for the breadcrumb link")
        assert ft.has_breadcrumb()

    def breadcrumb_navigation_to_list_verification(self, open_record, steps):
        """TC-LFT-027 — The breadcrumb navigates back to the list."""
        listing, ft, _ = open_record
        steps.append("Clicked the breadcrumb")
        ft.click_breadcrumb_to_list()
        listing.wait_for_list_page()

    def view_page_read_only_fields_verification(self, open_record, steps):
        """TC-LFT-028 — The view page exposes no editable controls."""
        _, ft, _ = open_record
        steps.append("Checked the view page for editable inputs")
        assert ft.is_view_read_only()

    def default_status_active_verification(self, open_record, steps):
        """TC-LFT-029 — A new record's Status reads Active."""
        _, ft, _ = open_record
        steps.append("Read the Status value")
        assert "active" in ft.view_field_text("Status").lower()

    def edit_button_opens_edit_page_verification(self, open_record, steps):
        """TC-LFT-030 — Edit is visible and opens the edit page."""
        _, ft, _ = open_record
        steps.append("Clicked Edit")
        ft.click_edit()

    def delete_button_opens_confirmation_modal_verification(self, open_record, steps):
        """TC-LFT-031 — Delete is visible and opens the confirmation modal."""
        _, ft, _ = open_record
        steps.append("Clicked Delete then cancelled")
        ft.click_delete()
        assert ft.get_delete_modal_title()
        ft.cancel_delete()

    def view_page_three_dot_menu_options_verification(self, open_record, steps):
        """TC-LFT-032 — The 3-dot menu has View audit trail and Object definition."""
        _, ft, _ = open_record
        steps.append("Opened the 3-dot More actions menu")
        ft.open_three_dot_menu()
        items = [i.lower() for i in ft.three_dot_menu_items()]
        assert any("audit trail" in i for i in items), items
        assert any("object definition" in i for i in items), items

    # ── Delete from the View page (modal contents, buttons, success) ───────────

    def view_page_delete_modal_title_verification(self, open_record, steps):
        """TC-LFT-032a — The delete modal opened from View is titled "Delete loan fee type"."""
        _, ft, _ = open_record
        steps.append("Clicked Delete on the View page")
        ft.click_delete()
        try:
            assert ft.get_delete_modal_title() == "Delete loan fee type"
        finally:
            ft.cancel_delete()

    def view_page_delete_modal_message_verification(self, open_record, steps):
        """TC-LFT-032b — The modal states what will be deleted and names the record."""
        _, ft, name = open_record
        ft.click_delete()
        try:
            body = ft.get_delete_modal_message()
            steps.append("Read the delete modal body text")
            assert "will be permanently deleted" in body, f"body was {body!r}"
            assert name in body, f"modal does not name {name!r}: {body!r}"
        finally:
            ft.cancel_delete()

    def view_page_delete_modal_buttons_verification(self, open_record, steps):
        """TC-LFT-032c — The modal offers exactly Delete and Cancel."""
        _, ft, _ = open_record
        ft.click_delete()
        try:
            dlg = ft.delete_dialog()
            steps.append("Checked the modal's action buttons")
            assert dlg.get_by_role("button", name="Delete").count() > 0, "no Delete button"
            assert dlg.get_by_role("button", name="Cancel").count() > 0, "no Cancel button"
        finally:
            ft.cancel_delete()

    @pytest.mark.xfail(
        reason="The delete modal has no Close (X) control — only Delete and Cancel",
        strict=False,
    )
    def view_page_delete_modal_close_button_verification(self, open_record, steps):
        """TC-LFT-032d — The modal should offer a Close (X) as well as Cancel."""
        _, ft, _ = open_record
        ft.click_delete()
        try:
            steps.append("Looked for a Close (X) control on the delete modal")
            assert ft.delete_dialog().get_by_role("button", name="Close").count() > 0
        finally:
            ft.cancel_delete()

    def view_page_delete_success_verification(self, fee_type_listing_page, fee_type_for_delete, steps):
        """TC-LFT-032e — Deleting from the View page removes the record and confirms."""
        from pages.loan_fee_type.fee_type_page import LoanFeeTypePage

        listing = fee_type_listing_page
        listing.search_by_name(fee_type_for_delete)
        listing.open_record_by_name(fee_type_for_delete)
        ft = LoanFeeTypePage(listing.page)
        ft.wait_for_view_page()

        steps.append("Deleted the record from its View page")
        ft.start_recording_toasts()
        ft.click_delete()
        ft.confirm_delete()
        toast = ft.wait_for_toast()

        listing.wait_for_list_page()
        listing.search_by_name(fee_type_for_delete)
        assert not listing.is_record_visible(fee_type_for_delete), "record still present"
        assert toast, "no confirmation message was shown after deleting"
        steps.append(f"Confirmation message: {toast!r}")


class TestEditLoanFeeType:

    @pytest.mark.xfail(
        reason="Bug #31 — the edit heading exposes the raw internal object path",
        strict=False,
    )
    def edit_page_title_verification(self, open_record, steps):
        """TC-LFT-033 — The edit title should not expose the object path."""
        _, ft, _ = open_record
        ft.click_edit()
        steps.append("Read the edit page H1")
        title = ft.get_page_title()
        assert OBJECT_PATH not in title, f"title was {title!r}"

    def edit_page_name_mandatory_marker_verification(self, open_record, steps):
        """TC-LFT-034 — Name carries the mandatory marker on the edit page."""
        _, ft, _ = open_record
        ft.click_edit()
        steps.append("Checked the mandatory marker on edit")
        assert ft.is_field_mandatory(ft.NAME_ARIA_LABEL)

    def record_rename_persistence_verification(self, open_record, steps):
        """TC-LFT-035 — A record can be renamed and the change persists."""
        listing, ft, name = open_record
        renamed = f"{name}_R"
        ft.click_edit()
        ft.fill_name(renamed)
        steps.append(f"Renamed the record to {renamed}")
        ft.save()
        try:
            ft.wait_for_view_page()
            listing.navigate_to_list()
            listing.search_by_name(renamed)
            assert listing.is_record_visible(renamed)
        finally:
            delete_if_present(listing, ft, renamed)

    @pytest.mark.xfail(
        reason="Bug #30 — the blank-name error on edit leaks the internal object path",
        strict=False,
    )
    def edit_page_blank_name_validation_message_verification(self, open_record, steps):
        """TC-LFT-036 — Blank and whitespace names on edit give readable errors."""
        _, ft, _ = open_record
        ft.click_edit()

        steps.append("Cleared the name and saved")
        ft.fill_name("")
        ft.save()
        ft.page.wait_for_timeout(2_000)
        blank = ft.error_banner_text()

        steps.append("Set a whitespace-only name and saved")
        ft.fill_name("   ")
        ft.save()
        ft.page.wait_for_timeout(2_000)
        space = ft.error_banner_text()

        assert blank and space, f"blank={blank!r} whitespace={space!r}"
        for banner in (blank, space):
            assert OBJECT_PATH not in banner, f"leaks the object path: {banner!r}"

    def gl_account_edit_persistence_verification(self, open_record, steps):
        """TC-LFT-037 — GL account can be changed and the change persists."""
        _, ft, _ = open_record
        ft.click_edit()
        steps.append("Changed the GL account")
        ft.set_gl_account(GL_ACCOUNT_QUERY)
        ft.save()
        ft.wait_for_view_page()
        assert GL_ACCOUNT_QUERY in ft.view_field_text("GL account")

    def item_edit_persistence_verification(self, open_record, steps):
        """TC-LFT-038 — Item can be set and the change persists."""
        _, ft, _ = open_record
        ft.click_edit()
        steps.append(f"Set Item to {ITEM_QUERY}")
        ft.set_item(ITEM_QUERY)
        ft.save()
        ft.wait_for_view_page()
        assert ITEM_QUERY in ft.view_field_text("Item")

    def status_edit_persistence_verification(self, open_record, steps):
        """TC-LFT-039 — Status can be switched to Inactive and persists."""
        _, ft, _ = open_record
        ft.click_edit()
        assert ft.has_status_field(), "no Status control on the edit page"
        steps.append("Set Status to Inactive")
        ft.set_status("Inactive")
        ft.save()
        ft.wait_for_view_page()
        assert "inactive" in ft.view_field_text("Status").lower()

    def description_edit_persistence_verification(self, open_record, steps):
        """TC-LFT-040 — Description can be edited and the change persists."""
        _, ft, _ = open_record
        text = "Automated edit check"
        ft.click_edit()
        steps.append("Set a Description")
        ft.fill_description(text)
        ft.save()
        ft.wait_for_view_page()
        assert text in ft.view_field_text("Description")

    def edit_save_redirects_to_detail_verification(self, open_record, steps):
        """TC-LFT-041 — Save on edit returns to the record's detail page."""
        _, ft, _ = open_record
        ft.click_edit()
        ft.fill_description("Redirect check")
        steps.append("Saved from the edit page")
        ft.save()
        ft.wait_for_view_page()
        assert "Loan fee type:" in ft.get_page_title()

    # ── Description max length on edit (500) ───────────────────────────────────

    def edit_page_description_accepts_500_characters_verification(self, open_record, steps):
        """TC-LFT-041a — A 500-character Description saves on the edit page."""
        _, ft, _ = open_record
        ft.click_edit()
        steps.append("Entered a 500-character Description and saved")
        ft.fill_description("E" * 500)
        ft.save()
        ft.wait_for_view_page()
        assert len(ft.view_field_text("Description")) >= 500

    @pytest.mark.xfail(
        reason="Same family as Bug #87 — Description has no maxlength on edit and the "
               "over-length error leaks the internal object path",
        strict=False,
    )
    def edit_page_description_maximum_length_validation_verification(self, open_record, steps):
        """TC-LFT-041b — Over-500 Description is capped or rejected readably on edit."""
        _, ft, _ = open_record
        ft.click_edit()
        steps.append("Entered a 510-character Description on the edit page")
        assert ft.get_description_maxlength() is not None, "input has no maxlength cap"
        ft.fill_description("E" * 510)
        ft.save()
        ft.page.wait_for_timeout(2_000)
        banner = ft.error_banner_text()
        assert banner, "an over-length Description was accepted with no error"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    # ── Success message on edit ────────────────────────────────────────────────

    def edit_success_confirmation_message_verification(self, open_record, steps):
        """TC-LFT-041c — Saving an edit shows a confirmation message."""
        _, ft, _ = open_record
        ft.click_edit()
        ft.fill_description("Confirmation message check")
        steps.append("Saved an edit and captured the confirmation")
        ft.start_recording_toasts()
        ft.save()
        toast = ft.wait_for_toast()
        ft.wait_for_view_page()
        assert toast, "no confirmation message was shown after saving an edit"
        steps.append(f"Confirmation message: {toast!r}")
