"""
test_create.py
=========================
Playwright / pytest tests for the CREATE stage of the Loan Fee Type module
(Lending Management → Setup → Loan fee type).

Checklist rows: TC-LFT-001 – TC-LFT-024 ("Loan Fee Type - CRUD", SL 1-24).
Verified live against release www-p303 / SNL_release_monthly / LME entity
on 2026-08-12.

Known open defects asserted here rather than worked around — each xfail names
the bug so a fix flips the test to XPASS instead of passing silently:
  * Bug #29 — the Name field is labelled "Loan type", not "Name" (SL 8).
  * Bug #30 — validation messages leak internal field/object names (SL 11, 16).
  * Bug #87 — the over-length message leaks the object path; no maxlength (SL 12).
  * Bug #88 — duplicate names are accepted (SL 22).
"""

import pytest
from playwright.sync_api import expect

from pages.loan_fee_type.fee_type_page import LoanFeeTypePage
from .conftest import GL_ACCOUNT_QUERY, ITEM_QUERY, delete_if_present

OBJECT_PATH = "loan-management/loan-fee-type"


class TestCreateLoanFeeType:

    # ── Page structure (SL 1-6) ────────────────────────────────────────────────

    def create_page_title_verification(self, create_form, steps):
        """TC-LFT-001 — Create page title is "Create loan fee type"."""
        steps.append("Read the create page H1")
        assert create_form.get_page_title() == "Create loan fee type"

    def create_page_information_section_verification(self, create_form, steps):
        """TC-LFT-002 — The form has a "Loan fee type information" section."""
        steps.append("Looked for the information section header")
        expect(
            create_form.frame.get_by_text(create_form.SECTION_HEADER, exact=False).first
        ).to_be_visible()

    def create_page_save_button_presence_verification(self, create_form, steps):
        """TC-LFT-003 — The Save split-button is present."""
        steps.append("Looked for the Save control")
        assert create_form.frame.locator(
            '[aria-label="Save"], [role=menuitem]:has-text("Save")'
        ).count() > 0

    def save_dropdown_options_verification(self, create_form, steps):
        """TC-LFT-004 — Save offers Save / Save and close / Save and new."""
        steps.append("Opened the Save split-button menu")
        opts = [o.lower() for o in create_form.save_menu_options()]
        for wanted in ("save", "save and close", "save and new"):
            assert any(o == wanted for o in opts), f"{wanted!r} missing from {opts}"

    def cancel_button_discards_new_record_verification(self, fee_type_listing_page, unique_fee_type_name, steps):
        """TC-LFT-005 — Cancel leaves the form without creating a record."""
        listing = fee_type_listing_page
        listing.click_create()
        ft = LoanFeeTypePage(listing.page)
        ft.fill_name(unique_fee_type_name)
        steps.append("Entered a name then clicked Cancel")
        ft.cancel()
        listing.wait_for_list_page()
        listing.search_by_name(unique_fee_type_name)
        try:
            assert not listing.is_record_visible(unique_fee_type_name)
        finally:
            delete_if_present(listing, ft, unique_fee_type_name)

    def create_page_back_arrow_presence_verification(self, create_form, steps):
        """TC-LFT-006 — The back arrow is present on the create page."""
        steps.append("Looked for the back arrow")
        assert create_form.has_back_arrow()

    # ── Name field (SL 7-12) ───────────────────────────────────────────────────

    def name_field_presence_and_mandatory_marker_verification(self, create_form, steps):
        """TC-LFT-007 — Name is present and marked mandatory."""
        steps.append("Checked the name field and its mandatory marker")
        assert create_form.frame.locator(create_form.NAME_INPUT).count() > 0
        assert create_form.is_field_mandatory(create_form.NAME_ARIA_LABEL)

    @pytest.mark.xfail(
        reason="Bug #29 — the Name field is labelled 'Loan type', not 'Name'",
        strict=False,
    )
    def name_field_label_verification(self, create_form, steps):
        """TC-LFT-008 — The name field should be labelled "Name"."""
        steps.append("Read the field labels on the create form")
        labels = [l.rstrip(" *").strip() for l in create_form.field_labels()]
        assert "Name" in labels, f"labels were {labels}"

    def create_record_with_valid_name_and_gl_account_verification(
        self, fee_type_listing_page, unique_fee_type_name, steps
    ):
        """TC-LFT-009 — A record saves with a valid name + GL account."""
        listing = fee_type_listing_page
        listing.click_create()
        ft = LoanFeeTypePage(listing.page)
        ft.fill_name(unique_fee_type_name)
        ft.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Saved a minimum-valid fee type")
        ft.save()
        try:
            ft.wait_for_view_page()
            assert "Loan fee type:" in ft.get_page_title()
        finally:
            delete_if_present(listing, ft, unique_fee_type_name)

    def blank_name_validation_message_verification(self, create_form, steps):
        """TC-LFT-010 — Saving with a blank name shows a field-required error."""
        create_form.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Saved with the name left blank")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text().lower()
        assert "required" in banner or "correct the fields" in banner, banner

    @pytest.mark.xfail(
        reason="Bug #30 — the whitespace-only name error leaks the internal object path",
        strict=False,
    )
    def whitespace_only_name_validation_message_verification(self, create_form, steps):
        """TC-LFT-011 — A whitespace-only name is rejected with a readable message."""
        create_form.fill_name("   ")
        create_form.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Saved with a whitespace-only name")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert banner, "no error was shown at all"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    @pytest.mark.xfail(
        reason="Bug #87 — no maxlength on the input and the error leaks the object path",
        strict=False,
    )
    def name_maximum_length_validation_verification(self, create_form, steps):
        """TC-LFT-012 — Name over 200 chars is rejected with a plain length message."""
        steps.append("Entered a 253-character name and saved")
        assert create_form.get_name_maxlength() is not None, "input has no maxlength cap"
        create_form.fill_name("QA" + "A" * 251)
        create_form.set_gl_account(GL_ACCOUNT_QUERY)
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert "length" in banner.lower()
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    # ── GL account (SL 13-16) ──────────────────────────────────────────────────

    def gl_account_field_mandatory_marker_verification(self, create_form, steps):
        """TC-LFT-013 — GL account is present and mandatory."""
        steps.append("Checked the GL account mandatory marker")
        assert create_form.is_field_mandatory("GL account")

    def gl_account_field_is_dropdown_verification(self, create_form, steps):
        """TC-LFT-014 — GL account renders as a combobox."""
        steps.append("Checked GL account is a combobox")
        assert create_form.frame.get_by_role("combobox", name="GL account").count() > 0

    def gl_account_dropdown_lists_accounts_verification(self, create_form, steps):
        """TC-LFT-015 — The GL account picker returns matching accounts."""
        steps.append(f"Searched the GL account picker for {GL_ACCOUNT_QUERY}")
        create_form.set_gl_account(GL_ACCOUNT_QUERY)
        assert GL_ACCOUNT_QUERY in create_form.get_gl_account_value()

    @pytest.mark.xfail(
        reason="Bug #30 — the error names the internal field 'feeGLAccountKey'",
        strict=False,
    )
    def missing_gl_account_validation_message_verification(
        self, create_form, unique_fee_type_name, steps
    ):
        """TC-LFT-016 — Saving without a GL account names the on-screen label."""
        create_form.fill_name(unique_fee_type_name)
        steps.append("Saved without selecting a GL account")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert banner, "no error was shown at all"
        assert "feeGLAccountKey" not in banner, f"names the internal field: {banner!r}"
        assert OBJECT_PATH not in banner, f"leaks the object path: {banner!r}"

    # ── Item / Description (SL 17-21) ──────────────────────────────────────────

    def item_field_optional_verification(self, create_form, steps):
        """TC-LFT-017 — Item is present and NOT mandatory."""
        steps.append("Checked Item is optional")
        assert create_form.has_field("Item")
        assert not create_form.is_field_mandatory("Item")

    def item_field_is_dropdown_verification(self, create_form, steps):
        """TC-LFT-018 — Item renders as a combobox."""
        steps.append("Checked Item is a combobox")
        assert create_form.frame.get_by_role("combobox", name="Item").count() > 0

    def item_dropdown_lists_items_verification(self, create_form, steps):
        """TC-LFT-019 — The Item picker returns matching inventory items."""
        steps.append(f"Searched the Item picker for {ITEM_QUERY}")
        create_form.set_item(ITEM_QUERY)
        assert create_form.get_item_value()

    def description_field_optional_verification(self, create_form, steps):
        """TC-LFT-020 — Description is present and NOT mandatory."""
        steps.append("Checked Description is optional")
        assert create_form.has_field("Description")
        assert not create_form.is_field_mandatory("Description")

    def description_accepts_500_characters_verification(
        self, fee_type_listing_page, unique_fee_type_name, steps
    ):
        """TC-LFT-020a — A 500-character Description saves on create."""
        listing = fee_type_listing_page
        listing.click_create()
        ft = LoanFeeTypePage(listing.page)
        ft.fill_name(unique_fee_type_name)
        ft.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Entered a 500-character Description and saved")
        ft.fill_description("D" * 500)
        ft.save()
        try:
            ft.wait_for_view_page()
            assert len(ft.view_field_text("Description")) >= 500
        finally:
            delete_if_present(listing, ft, unique_fee_type_name)

    @pytest.mark.xfail(
        reason="Same family as Bug #87 — Description has no maxlength attribute and the "
               "over-500 error leaks the internal object path",
        strict=False,
    )
    def description_maximum_length_validation_verification(self, create_form, steps):
        """TC-LFT-020b — Over-500 Description is capped or rejected readably."""
        steps.append("Entered a 510-character Description")
        assert create_form.get_description_maxlength() is not None, (
            "Description input has no maxlength cap"
        )
        create_form.fill_name("AutoDescLen")
        create_form.set_gl_account(GL_ACCOUNT_QUERY)
        create_form.fill_description("D" * 510)
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert banner, "an over-length Description was accepted with no error"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    def save_without_optional_fields_verification(
        self, fee_type_listing_page, unique_fee_type_name, steps
    ):
        """TC-LFT-021 — The form saves with Item and Description left blank."""
        listing = fee_type_listing_page
        listing.click_create()
        ft = LoanFeeTypePage(listing.page)
        ft.fill_name(unique_fee_type_name)
        ft.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Saved with Item and Description empty")
        ft.save()
        try:
            ft.wait_for_view_page()
        finally:
            delete_if_present(listing, ft, unique_fee_type_name)

    # ── Duplicate handling + save variants (SL 22-24) ──────────────────────────

    @pytest.mark.api
    @pytest.mark.xfail(
        reason="Bug #88 — duplicate fee type names are accepted on create",
        strict=False,
    )
    def duplicate_name_rejection_verification(
        self, fee_type_listing_page, unique_fee_type_name, steps
    ):
        """TC-LFT-022 — A second record with an existing name must be rejected."""
        listing = fee_type_listing_page
        ft = LoanFeeTypePage(listing.page)
        try:
            listing.click_create()
            ft.fill_name(unique_fee_type_name)
            ft.set_gl_account(GL_ACCOUNT_QUERY)
            ft.save()
            ft.wait_for_view_page()

            steps.append("Attempted a second record with the identical name")
            listing.navigate_to_list()
            listing.click_create()
            ft.fill_name(unique_fee_type_name)
            ft.set_gl_account(GL_ACCOUNT_QUERY)
            ft.save()
            ft.page.wait_for_timeout(2_500)

            banner = ft.error_banner_text().lower()
            assert "exist" in banner or "duplicate" in banner, (
                f"the duplicate saved with no error (banner={banner!r})"
            )
        finally:
            # A duplicate may have been created — remove every copy.
            for _ in range(2):
                delete_if_present(listing, ft, unique_fee_type_name)

    def save_creates_record_and_opens_detail_verification(
        self, fee_type_listing_page, unique_fee_type_name, steps
    ):
        """TC-LFT-023 — Save creates the record and opens its detail page."""
        listing = fee_type_listing_page
        listing.click_create()
        ft = LoanFeeTypePage(listing.page)
        ft.fill_name(unique_fee_type_name)
        ft.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Clicked Save")
        ft.save()
        try:
            ft.wait_for_view_page()
            assert ft.view_field_text("GL account") != "--"
        finally:
            delete_if_present(listing, ft, unique_fee_type_name)

    def create_success_confirmation_message_verification(
        self, fee_type_listing_page, unique_fee_type_name, steps
    ):
        """
        TC-LFT-023a — Creating a record shows a confirmation message.

        The toast is short-lived, so recording starts before Save; reading after
        the redirect would miss it and wrongly look like no message at all.
        """
        listing = fee_type_listing_page
        listing.click_create()
        ft = LoanFeeTypePage(listing.page)
        ft.fill_name(unique_fee_type_name)
        ft.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Armed the toast recorder, then saved")
        ft.start_recording_toasts()
        ft.save()
        toast = ft.wait_for_toast()
        try:
            assert toast, "no confirmation message was shown after creating a record"
            assert "fee type" in toast.lower(), (
                f"confirmation does not name the object: {toast!r}"
            )
            steps.append(f"Confirmation message: {toast!r}")
        finally:
            delete_if_present(listing, ft, unique_fee_type_name)

    def save_and_close_returns_to_list_verification(
        self, fee_type_listing_page, unique_fee_type_name, steps
    ):
        """TC-LFT-024 — "Save and close" creates the record and returns to the list."""
        listing = fee_type_listing_page
        listing.click_create()
        ft = LoanFeeTypePage(listing.page)
        ft.fill_name(unique_fee_type_name)
        ft.set_gl_account(GL_ACCOUNT_QUERY)
        steps.append("Saved using 'Save and close'")
        ft.save_via("Save and close")
        ft.page.wait_for_timeout(2_500)
        try:
            listing.wait_for_list_page()
            listing.search_by_name(unique_fee_type_name)
            assert listing.is_record_visible(unique_fee_type_name)
        finally:
            delete_if_present(listing, ft, unique_fee_type_name)
