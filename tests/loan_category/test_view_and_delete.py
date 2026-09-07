"""
test_view_and_delete.py
=========================
Playwright / pytest tests for the VIEW and DELETE stages of the Loan account
category module.

Checklist rows: TC-LC-030 – TC-LC-043 ("Loan Category - CRUD", SL 30-43).
Verified live against release www-p303 / SNL_release_monthly / LME entity
on 2026-08-17.

Known open defects asserted as xfail (a fix flips them to XPASS):
  * SL 30 — the view title reads "Loan account categories: <ID>" (plural noun
    plus the internal record ID) instead of naming the record.
  * SL 43 — the 3-dot menu offers only "View audit trail"; "Object definition"
    is missing (the app-wide missing-Object-definition defect).

Also covered beyond the checklist wording: the delete modal's own title says
"Delete loan category" while its body says "loan account category" — an
internal inconsistency, asserted explicitly so a wording fix is noticed.
"""

import pytest

from .conftest import delete_if_present


class TestViewLoanCategory:

    @pytest.mark.xfail(
        reason="SL 30 — the view title shows the plural noun and the internal record "
               "ID instead of the category name",
        strict=False,
    )
    def test_verify_that_the_view_page_title_identifies_the_category(self, open_record, steps):
        """TC-LC-030 — The view title should read "Loan account category: <Name>"."""
        _, cp, name = open_record
        steps.append("Read the view page H1")
        title = cp.get_page_title()
        assert name in title, f"title was {title!r}"

    def test_verify_that_the_loan_account_categories_breadcrumb_is_present(self, open_record, steps):
        """TC-LC-031 — A "Loan account categories" option is present."""
        _, cp, _ = open_record
        steps.append("Looked for the breadcrumb link")
        assert cp.has_breadcrumb()

    def test_verify_that_the_breadcrumb_returns_to_the_category_list(self, open_record, steps):
        """TC-LC-032 — Clicking it returns to the lister."""
        listing, cp, _ = open_record
        steps.append("Clicked the breadcrumb")
        cp.click_breadcrumb_to_list()
        listing.wait_for_list_page()

    def test_verify_that_all_fields_are_read_only_on_the_view_page(self, open_record, steps):
        """TC-LC-033 — All field values are read-only on the view page."""
        _, cp, _ = open_record
        steps.append("Checked the view page for editable controls")
        assert cp.is_view_read_only()

    def test_verify_that_a_new_category_has_active_status_by_default(self, open_record, steps):
        """TC-LC-034 — Status is Active by default."""
        _, cp, _ = open_record
        steps.append("Read the Status value")
        assert "active" in cp.view_field_text("Status").lower()

    def test_verify_that_the_edit_button_opens_the_edit_page(self, open_record, steps):
        """TC-LC-035 — Edit is visible and functional."""
        _, cp, _ = open_record
        steps.append("Clicked Edit")
        cp.click_edit()

    def test_verify_that_the_delete_button_opens_the_confirmation_window(self, open_record, steps):
        """TC-LC-036 / TC-LC-037 — Delete opens the confirmation modal."""
        _, cp, _ = open_record
        steps.append("Clicked Delete")
        cp.click_delete()
        try:
            assert cp.get_delete_modal_title()
        finally:
            cp.cancel_delete()

    def test_verify_that_the_delete_window_has_a_title_delete_and_cancel_buttons(self, open_record, steps):
        """TC-LC-038 — The modal has a title plus Delete and Cancel buttons."""
        _, cp, _ = open_record
        cp.click_delete()
        try:
            dlg = cp.delete_dialog()
            steps.append("Inspected the modal title and buttons")
            assert cp.get_delete_modal_title()
            assert dlg.get_by_role("button", name="Delete").count() > 0
            assert dlg.get_by_role("button", name="Cancel").count() > 0
        finally:
            cp.cancel_delete()

    def test_verify_that_the_delete_window_displays_the_expected_title(self, open_record, steps):
        """
        TC-LC-039 — The modal displays its title correctly.

        Recorded as observed: the title is "Delete loan category" while the body
        and every other heading call the object a "loan account category".
        """
        _, cp, _ = open_record
        cp.click_delete()
        try:
            steps.append("Read the modal title")
            assert cp.get_delete_modal_title() == "Delete loan category"
        finally:
            cp.cancel_delete()

    def test_verify_that_the_delete_window_names_the_category_in_its_message(self, open_record, steps):
        """TC-LC-040 — The modal shows a confirmation message naming the record."""
        _, cp, name = open_record
        cp.click_delete()
        try:
            body = cp.get_delete_modal_message()
            steps.append("Read the modal body")
            assert "will be permanently deleted" in body, f"body was {body!r}"
            assert name in body, f"modal does not name {name!r}"
        finally:
            cp.cancel_delete()

    def test_verify_that_cancelling_delete_keeps_the_category(self, open_record, steps):
        """TC-LC-041 — Cancel closes the modal without deleting."""
        listing, cp, name = open_record
        cp.click_delete()
        steps.append("Cancelled the delete")
        cp.cancel_delete()
        listing.navigate_to_list()
        listing.search_by_name(name)
        assert listing.is_record_visible(name)

    def test_verify_that_confirming_delete_removes_the_category_and_returns_to_the_list(
        self, category_listing_page, category_for_delete, steps
    ):
        """TC-LC-042 — Confirming Delete removes the record and returns to the list."""
        from pages.loan_category.category_page import LoanCategoryPage

        listing = category_listing_page
        listing.search_by_name(category_for_delete)
        listing.open_record_by_name(category_for_delete)
        cp = LoanCategoryPage(listing.page)
        cp.wait_for_view_page()

        steps.append("Confirmed the delete")
        cp.click_delete()
        cp.confirm_delete()
        listing.wait_for_list_page()
        listing.search_by_name(category_for_delete)
        assert not listing.is_record_visible(category_for_delete)

    def test_verify_that_deleting_a_category_shows_a_confirmation_message(
        self, category_listing_page, category_for_delete, steps
    ):
        """TC-LC-042a — Deleting shows a confirmation message."""
        from pages.loan_category.category_page import LoanCategoryPage

        listing = category_listing_page
        listing.search_by_name(category_for_delete)
        listing.open_record_by_name(category_for_delete)
        cp = LoanCategoryPage(listing.page)
        cp.wait_for_view_page()

        steps.append("Armed the toast recorder, then confirmed the delete")
        cp.start_recording_toasts()
        cp.click_delete()
        cp.confirm_delete()
        toast = cp.wait_for_toast()
        listing.wait_for_list_page()
        assert toast, "no confirmation message was shown after deleting"
        steps.append(f"Confirmation message: {toast!r}")

    @pytest.mark.xfail(
        reason="SL 43 — the 3-dot menu offers only 'View audit trail'; "
               "'Object definition' is missing",
        strict=False,
    )
    def test_verify_that_the_more_actions_menu_contains_the_expected_options(self, open_record, steps):
        """TC-LC-043 — The 3-dot menu has View audit trail and Object definition."""
        _, cp, _ = open_record
        steps.append("Opened the 3-dot More actions menu")
        cp.open_three_dot_menu()
        items = [i.lower() for i in cp.three_dot_menu_items()]
        assert any("audit trail" in i for i in items), items
        assert any("object definition" in i for i in items), items
