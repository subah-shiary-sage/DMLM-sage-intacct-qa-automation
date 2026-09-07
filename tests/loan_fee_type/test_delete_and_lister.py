"""
test_delete_and_lister.py
=========================
Playwright / pytest tests for the DELETE stage, the general/accessibility rows,
and the Loan fee types lister.

Checklist rows:
  * TC-LFT-042 – TC-LFT-050 ("Loan Fee Type - CRUD", SL 42-50)
  * TC-LFT-L10 – TC-LFT-L12 ("Config Listers LT-LIR-LC-LFT", SL 10-12)

Verified live against release www-p303 / SNL_release_monthly / LME entity
on 2026-08-12.

Test data: every record these tests create is prefixed and deleted afterwards.
The bulk-delete tests select only rows they created and assert the selection
count first, so a pre-existing record can never be caught in a bulk delete.

Known open defects asserted as xfail:
  * Bug #43 / IAUI-616 — untranslated resource keys leak into the UI (SL 47,
    and the lister's BULK_SELECTED column header).
  * Provisional #89 — the bulk-delete modal is empty (SL 49).
  * Provisional #90 — the bulk-delete toast names the wrong object (SL 50).
"""

import pytest

from pages.loan_fee_type.fee_type_page import LoanFeeTypePage
from .conftest import GL_ACCOUNT_QUERY, delete_if_present

IN_USE_FEE_TYPE = "Loan Fee Type 02"


class TestDeleteLoanFeeType:

    def _open(self, listing, name):
        listing.search_by_name(name)
        listing.open_record_by_name(name)
        ft = LoanFeeTypePage(listing.page)
        ft.wait_for_view_page()
        return ft

    def delete_opens_confirmation_modal_verification(
        self, fee_type_listing_page, fee_type_for_delete, steps
    ):
        """TC-LFT-042 — Delete opens a confirmation modal."""
        listing = fee_type_listing_page
        ft = self._open(listing, fee_type_for_delete)
        steps.append("Clicked Delete")
        ft.click_delete()
        try:
            assert ft.get_delete_modal_title()
        finally:
            ft.cancel_delete()
            delete_if_present(listing, ft, fee_type_for_delete)

    def delete_modal_components_verification(
        self, fee_type_listing_page, fee_type_for_delete, steps
    ):
        """TC-LFT-043 — The modal has a title, message, Delete and Cancel."""
        listing = fee_type_listing_page
        ft = self._open(listing, fee_type_for_delete)
        ft.click_delete()
        try:
            dlg = ft.delete_dialog()
            steps.append("Inspected the modal's title, body and buttons")
            assert ft.get_delete_modal_title()
            assert ft.get_delete_modal_message()
            assert dlg.get_by_role("button", name="Delete").count() > 0
            assert dlg.get_by_role("button", name="Cancel").count() > 0
        finally:
            ft.cancel_delete()
            delete_if_present(listing, ft, fee_type_for_delete)

    def delete_modal_names_record_verification(
        self, fee_type_listing_page, fee_type_for_delete, steps
    ):
        """TC-LFT-044 — The modal names the record being deleted."""
        listing = fee_type_listing_page
        ft = self._open(listing, fee_type_for_delete)
        ft.click_delete()
        try:
            steps.append("Read the modal body")
            assert fee_type_for_delete in ft.get_delete_modal_message()
        finally:
            ft.cancel_delete()
            delete_if_present(listing, ft, fee_type_for_delete)

    def delete_cancel_retains_record_verification(
        self, fee_type_listing_page, fee_type_for_delete, steps
    ):
        """TC-LFT-045 — Cancel closes the modal without deleting."""
        listing = fee_type_listing_page
        ft = self._open(listing, fee_type_for_delete)
        ft.click_delete()
        steps.append("Cancelled the delete")
        ft.cancel_delete()
        try:
            listing.navigate_to_list()
            listing.search_by_name(fee_type_for_delete)
            assert listing.is_record_visible(fee_type_for_delete)
        finally:
            delete_if_present(listing, ft, fee_type_for_delete)

    def delete_confirmation_removes_record_verification(
        self, fee_type_listing_page, fee_type_for_delete, steps
    ):
        """TC-LFT-046 — Confirming Delete removes the record and returns to the list."""
        listing = fee_type_listing_page
        ft = self._open(listing, fee_type_for_delete)
        ft.click_delete()
        steps.append("Confirmed the delete")
        ft.confirm_delete()
        listing.wait_for_list_page()
        listing.search_by_name(fee_type_for_delete)
        assert not listing.is_record_visible(fee_type_for_delete)

    def delete_success_confirmation_message_verification(
        self, fee_type_listing_page, fee_type_for_delete, steps
    ):
        """TC-LFT-046a — Deleting a record shows a confirmation message."""
        listing = fee_type_listing_page
        ft = self._open(listing, fee_type_for_delete)
        steps.append("Armed the toast recorder, then confirmed the delete")
        ft.start_recording_toasts()
        ft.click_delete()
        ft.confirm_delete()
        toast = ft.wait_for_toast()
        listing.wait_for_list_page()
        assert toast, "no confirmation message was shown after deleting"
        steps.append(f"Confirmation message: {toast!r}")


class TestGeneralAndAccessibility:

    @pytest.mark.xfail(
        reason="Bug #43 / IAUI-616 — untranslated IA.* / BULK_SELECTED keys leak into the UI",
        strict=False,
    )
    def accessibility_label_translation_verification(self, create_form, steps):
        """TC-LFT-047 — No raw resource keys are used as labels."""
        steps.append("Scanned the create form for untranslated resource keys")
        leaked = create_form.untranslated_aria_keys()
        assert not leaked, f"untranslated keys present: {sorted(leaked)}"

    @pytest.mark.skip(
        reason="Needs a fee type referenced by a loan type's Fee row. "
               "SNL_release_monthly has no such fixture, and creating it would mean "
               "editing a loan type. Verify manually or seed the fixture first."
    )
    def in_use_record_edit_allowed_delete_blocked_verification(self, fee_type_listing_page):
        """TC-LFT-048 — An in-use fee type stays editable but cannot be deleted."""


class TestBulkDelete:
    """
    Bulk delete on the lister.

    Both tests create their own records and assert that exactly those rows are
    selected before confirming, so no pre-existing record can be deleted.
    """

    def _seed(self, listing, count=2):
        import uuid

        ft = LoanFeeTypePage(listing.page)
        names = []
        for _ in range(count):
            name = f"AutoBulk_{uuid.uuid4().hex[:8].upper()}"
            listing.navigate_to_list()
            listing.click_create()
            ft.fill_name(name)
            ft.set_gl_account(GL_ACCOUNT_QUERY)
            ft.save()
            ft.wait_for_view_page()
            names.append(name)
        return ft, names

    def _select_only(self, listing, names):
        """Select exactly `names`; returns True only if nothing else is ticked."""
        listing.navigate_to_list()
        listing.search_by_name("AutoBulk_")
        picked = sum(1 for n in names if listing.select_row_by_name(n))
        return picked == len(names) and listing.selected_count() == picked

    @pytest.mark.xfail(
        reason="Provisional #89 — the bulk-delete modal has no title, message or record list",
        strict=False,
    )
    def bulk_delete_modal_content_verification(self, fee_type_listing_page, steps):
        """TC-LFT-049 — The bulk-delete modal names what will be deleted."""
        listing = fee_type_listing_page
        ft, names = self._seed(listing)
        try:
            assert self._select_only(listing, names), "refusing to bulk-delete: selection mismatch"
            steps.append(f"Selected {len(names)} rows and opened bulk Delete")
            listing.click_bulk_delete()
            dlg = listing.bulk_delete_dialog()
            body = (dlg.inner_text() or "").strip()
            assert dlg.get_by_role("heading").count() > 0, f"modal has no title (body={body!r})"
            assert any(n in body for n in names), f"modal does not list the records (body={body!r})"
        finally:
            try:
                listing.bulk_delete_dialog().get_by_role("button", name="Cancel").first.click()
            except Exception:
                pass
            for n in names:
                delete_if_present(listing, ft, n)

    @pytest.mark.xfail(
        reason="Provisional #90 — the bulk-delete toast reads 'Loan types deleted'",
        strict=False,
    )
    def bulk_delete_confirmation_message_verification(self, fee_type_listing_page, steps):
        """TC-LFT-050 — The bulk-delete confirmation names loan fee types."""
        listing = fee_type_listing_page
        ft, names = self._seed(listing)
        deleted = False
        try:
            assert self._select_only(listing, names), "refusing to bulk-delete: selection mismatch"
            steps.append("Confirmed the bulk delete")
            ft.start_recording_toasts()
            listing.click_bulk_delete()
            listing.bulk_delete_dialog().get_by_role("button", name="Delete").first.click()
            deleted = True
            toast = ft.wait_for_toast()
            assert toast, "no confirmation message was shown after the bulk delete"
            assert "loan fee type" in toast.lower(), f"toast read {toast!r}"
        finally:
            if not deleted:
                for n in names:
                    delete_if_present(listing, ft, n)


class TestLoanFeeTypeLister:

    @pytest.mark.xfail(
        reason="Bug #43 family — the first column header is the raw key BULK_SELECTED",
        strict=False,
    )
    def lister_column_names_verification(self, fee_type_listing_page, steps):
        """TC-LFT-L10 — Lister column headers contain no raw resource keys."""
        steps.append("Read the lister column headers")
        headers = fee_type_listing_page.get_column_headers()
        leaked = [h for h in headers if h.startswith("IA.") or h == "BULK_SELECTED"]
        assert not leaked, f"raw keys in headers: {leaked} (all: {headers})"

    def lister_name_filter_verification(
        self, fee_type_listing_page, created_fee_type, steps
    ):
        """TC-LFT-L11 — The Name filter narrows the grid to matching rows."""
        listing = fee_type_listing_page
        listing.navigate_to_list()
        steps.append(f"Filtered the Name column by {created_fee_type}")
        listing.search_by_name(created_fee_type)
        rows = listing.row_names()
        listing.clear_search()
        assert rows == [created_fee_type], f"filter returned {rows}"

    def lister_grid_data_rendering_verification(
        self, fee_type_listing_page, created_fee_type, steps
    ):
        """TC-LFT-L12 — The grid renders records under Name and Status."""
        listing = fee_type_listing_page
        listing.navigate_to_list()
        listing.search_by_name(created_fee_type)
        steps.append("Checked the grid renders the seeded record")
        assert created_fee_type in listing.row_names()
        assert {"Name", "Status"} <= set(listing.get_column_headers())
