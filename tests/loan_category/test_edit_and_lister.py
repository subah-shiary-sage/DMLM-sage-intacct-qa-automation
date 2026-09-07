"""
test_edit_and_lister.py
=========================
Playwright / pytest tests for the EDIT stage of the Loan account category
module, plus its lister.

Checklist rows:
  * TC-LC-044 – TC-LC-068 ("Loan Category - CRUD", SL 44-68)
  * TC-LC-L07 – TC-LC-L09 ("Config Listers LT-LIR-LC-LFT", SL 7-9)

Verified live against release www-p303 / SNL_release_monthly / LME entity
on 2026-08-17.

Checklist wording vs. observed behaviour:
  * SL 59 says the Description cap on edit is 500 and SL 60 says 1000. The app
    enforces 500 on both create and edit, so 500 is asserted.
  * SL 66 is API-level and skipped with a reason.
  * SL 68 (field-lock when the category is assigned to a loan account) needs a
    category attached to a loan account; that fixture does not exist in this
    company and is not manufactured here.
"""

import pytest

from pages.loan_category.category_page import LoanCategoryPage
from .conftest import DESCRIPTION_MAX, NAME_MAX, OBJECT_PATH, delete_if_present


class TestEditLoanCategory:

    # ── Page structure (SL 44-45, 52) ──────────────────────────────────────────

    def test_verify_that_the_edit_page_title_identifies_the_category(self, open_record, steps):
        """TC-LC-044 — The edit page title identifies the record being edited."""
        _, cp, name = open_record
        cp.click_edit()
        steps.append("Read the edit page H1")
        title = cp.get_page_title()
        assert "Edit" in title, f"title was {title!r}"

    def test_verify_that_the_name_field_is_required_on_the_edit_page(self, open_record, steps):
        """TC-LC-045 — Name is mandatory on the edit page."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Checked the Name mandatory marker on edit")
        assert cp.is_field_mandatory("Name")

    def test_verify_that_the_save_control_is_visible_on_the_edit_page(self, open_record, steps):
        """TC-LC-052 — The Save control is visible on the edit page."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Looked for the Save control on edit")
        assert cp.frame.locator(
            '[aria-label="Save"], [role=menuitem]:has-text("Save")'
        ).count() > 0

    # ── Name on edit (SL 46-51) ────────────────────────────────────────────────

    def test_verify_that_a_category_can_be_renamed_and_the_change_is_saved(self, open_record, steps):
        """TC-LC-046 — A record can be renamed and the change persists."""
        listing, cp, name = open_record
        renamed = f"{name}_R"
        cp.click_edit()
        cp.fill_name(renamed)
        steps.append(f"Renamed the record to {renamed}")
        cp.save()
        try:
            cp.wait_for_view_page()
            listing.navigate_to_list()
            listing.search_by_name(renamed)
            assert listing.is_record_visible(renamed)
        finally:
            delete_if_present(listing, cp, renamed)

    def test_verify_that_the_name_field_accepts_200_characters_on_edit(self, open_record, steps):
        """TC-LC-047 — Name accepts 200 characters on edit."""
        listing, cp, name = open_record
        long_name = "E" * NAME_MAX
        cp.click_edit()
        steps.append(f"Renamed to a {NAME_MAX}-character name")
        cp.fill_name(long_name)
        cp.save()
        try:
            cp.wait_for_view_page()
            assert len(cp.view_field_text("Name")) >= NAME_MAX
        finally:
            delete_if_present(listing, cp, long_name)
            delete_if_present(listing, cp, name)

    @pytest.mark.xfail(
        reason="No maxlength on the Name input and the over-length error leaks the "
               "internal object path (same family as Bug #87)",
        strict=False,
    )
    def test_verify_that_a_name_longer_than_200_characters_is_rejected_on_edit(self, open_record, steps):
        """TC-LC-048 — Over-200 name on edit is capped or rejected readably."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append(f"Entered a {NAME_MAX + 1}-character name on edit")
        assert cp.get_name_maxlength() is not None, "Name input has no maxlength cap"
        cp.fill_name("E" * (NAME_MAX + 1))
        cp.save()
        cp.page.wait_for_timeout(2_000)
        banner = cp.error_banner_text()
        assert banner, "an over-length name was accepted on edit"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    def test_verify_that_a_blank_name_is_rejected_on_edit(self, open_record, steps):
        """TC-LC-049 — An empty name on edit is rejected."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Cleared the name and saved")
        cp.fill_name("")
        cp.save()
        cp.page.wait_for_timeout(2_000)
        assert cp.error_banner_text(), "an empty name was accepted on edit"

    @pytest.mark.xfail(
        reason="The whitespace-only name error leaks the internal object path "
               "(same family as Bug #30)",
        strict=False,
    )
    def test_verify_that_a_whitespace_only_name_shows_a_readable_error_on_edit(self, open_record, steps):
        """TC-LC-050 — A whitespace-only name on edit gives a readable error."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Set a whitespace-only name and saved")
        cp.fill_name("   ")
        cp.save()
        cp.page.wait_for_timeout(2_000)
        banner = cp.error_banner_text()
        assert banner, "a whitespace-only name was accepted on edit"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    def test_verify_that_a_name_with_control_characters_is_not_silently_saved_on_edit(self, open_record, steps):
        """TC-LC-051 — A control-character name on edit is not silently accepted."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Set a control-character name and saved")
        cp.fill_name("\t\n")
        cp.save()
        cp.page.wait_for_timeout(2_000)
        assert "Edit" in cp.get_page_title() or cp.error_banner_text()

    # ── Save behaviour on edit (SL 53-55) ──────────────────────────────────────

    def test_verify_that_saving_an_edit_returns_to_the_detail_page(self, open_record, steps):
        """TC-LC-053 — Save updates the record and returns to the detail page."""
        _, cp, _ = open_record
        cp.click_edit()
        cp.fill_description("Redirect check")
        steps.append("Saved from the edit page")
        cp.save()
        cp.wait_for_view_page()
        assert cp.VIEW_HEADING_PREFIX in cp.get_page_title()

    def test_verify_that_saving_invalid_edits_shows_validation_errors(self, open_record, steps):
        """TC-LC-054 / TC-LC-055 — Validation errors appear when Save is clicked."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Cleared the mandatory name and saved")
        cp.fill_name("")
        cp.save()
        cp.page.wait_for_timeout(2_000)
        assert cp.error_banner_text() or cp.has_inline_field_error()

    def test_verify_that_saving_an_edit_shows_a_confirmation_message(self, open_record, steps):
        """TC-LC-053a — Saving an edit shows a confirmation message."""
        _, cp, _ = open_record
        cp.click_edit()
        cp.fill_description("Confirmation message check")
        steps.append("Armed the toast recorder, then saved")
        cp.start_recording_toasts()
        cp.save()
        toast = cp.wait_for_toast()
        cp.wait_for_view_page()
        assert toast, "no confirmation message was shown after saving an edit"
        steps.append(f"Confirmation message: {toast!r}")

    # ── Description on edit (SL 56-60) ─────────────────────────────────────────

    def test_verify_that_the_description_field_is_optional_on_edit(self, open_record, steps):
        """TC-LC-056 — Description is not mandatory on edit."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Checked Description has no mandatory marker on edit")
        assert not cp.is_field_mandatory("Description")

    def test_verify_that_the_description_field_accepts_500_characters_on_edit(self, open_record, steps):
        """TC-LC-057 — A 500-character description is accepted on edit."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append(f"Entered a {DESCRIPTION_MAX}-character description")
        cp.fill_description("D" * DESCRIPTION_MAX)
        cp.save()
        cp.wait_for_view_page()
        assert len(cp.view_field_text("Description")) >= DESCRIPTION_MAX

    def test_verify_that_an_empty_description_can_be_saved_on_edit(self, open_record, steps):
        """TC-LC-058 — An empty description is accepted on edit."""
        _, cp, _ = open_record
        cp.click_edit()
        cp.fill_description("temporary")
        cp.save()
        cp.wait_for_view_page()
        cp.click_edit()
        steps.append("Cleared the description and saved")
        cp.fill_description("")
        cp.save()
        cp.wait_for_view_page()

    def test_verify_that_a_description_longer_than_500_characters_is_rejected_on_edit(self, open_record, steps):
        """
        TC-LC-059 — An over-long description is rejected on edit.

        The checklist gives 500 here and 1000 on SL 60; the app enforces 500.
        """
        _, cp, _ = open_record
        cp.click_edit()
        steps.append(f"Entered a {DESCRIPTION_MAX + 1}-character description on edit")
        cp.fill_description("D" * (DESCRIPTION_MAX + 1))
        cp.save()
        cp.page.wait_for_timeout(2_000)
        assert cp.error_banner_text(), (
            f"a {DESCRIPTION_MAX + 1}-character description was accepted on edit"
        )

    @pytest.mark.xfail(
        reason="The over-length description error leaks the internal object path "
               "(same family as Bug #87)",
        strict=False,
    )
    def test_verify_that_an_overlength_description_shows_a_readable_error_on_edit(self, open_record, steps):
        """TC-LC-060 — The over-length description message should be readable."""
        _, cp, _ = open_record
        cp.click_edit()
        cp.fill_description("D" * (DESCRIPTION_MAX + 1))
        cp.save()
        cp.page.wait_for_timeout(2_000)
        banner = cp.error_banner_text()
        assert banner, "no error was shown"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    # ── Document sequence on edit (SL 61-66) ───────────────────────────────────

    def test_verify_that_the_document_sequence_field_is_optional_on_edit(self, open_record, steps):
        """TC-LC-062 / TC-LC-065 — Document sequence is optional on edit."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Checked Document sequence is optional on edit")
        assert not cp.is_field_mandatory("Document sequence")

    def test_verify_that_a_valid_document_sequence_can_be_saved_on_edit(self, open_record, steps):
        """TC-LC-061 — A valid document sequence is accepted on edit."""
        _, cp, _ = open_record
        cp.click_edit()
        options = cp.document_sequence_options()
        if not options:
            pytest.skip(
                "No document sequences are defined in this company, so a valid "
                "value cannot be selected on edit. Seed one to cover this row."
            )
        steps.append(f"Selected document sequence {options[0]!r}")
        cp.fill_document_sequence(options[0])
        cp.save()
        cp.wait_for_view_page()

    def test_verify_that_an_invalid_document_sequence_is_not_silently_saved_on_edit(self, open_record, steps):
        """TC-LC-064 — An invalid document sequence is not silently accepted on edit."""
        _, cp, _ = open_record
        cp.click_edit()
        steps.append("Typed a special-character document sequence on edit")
        cp.type_document_sequence("!!!@@@###")
        cp.save()
        cp.page.wait_for_timeout(2_000)
        value = cp.get_document_sequence_value()
        assert cp.error_banner_text() or value != "!!!@@@###"

    def test_verify_that_a_document_sequence_cannot_be_reused_on_edit(self, open_record, steps):
        """TC-LC-063 — A document sequence already in use is rejected on edit."""
        listing, cp, name = open_record
        cp.click_edit()
        options = cp.document_sequence_options()
        if not options:
            pytest.skip(
                "No document sequences defined in this company, so reuse cannot be "
                "exercised on edit. Seed one to cover this row."
            )
        other = f"{name}_OTHER"
        try:
            cp.fill_document_sequence(options[0])
            cp.save()
            cp.wait_for_view_page()

            steps.append("Created a second record and reused the same document sequence")
            listing.navigate_to_list()
            listing.click_create()
            cp.fill_name(other)
            cp.save()
            cp.wait_for_view_page()
            cp.click_edit()
            cp.fill_document_sequence(options[0])
            cp.save()
            cp.page.wait_for_timeout(2_500)
            assert cp.error_banner_text(), "a reused document sequence was accepted on edit"
        finally:
            delete_if_present(listing, cp, other)

    @pytest.mark.skip(
        reason="API-level only — a malformed request body cannot be produced through "
               "the UI, where Document sequence is a picker."
    )
    def test_verify_that_a_malformed_document_sequence_request_returns_an_error_on_edit(self):
        """TC-LC-066 — Malformed document-sequence request returns a proper error."""

    # ── Location / field lock (SL 67-68) ───────────────────────────────────────

    def test_verify_that_the_category_can_be_edited_from_its_detail_page(self, open_record, steps):
        """TC-LC-067 — The record can be edited from its detail page."""
        _, cp, _ = open_record
        steps.append("Opened Edit from the record's detail page")
        cp.click_edit()
        assert "Edit" in cp.get_page_title()

    @pytest.mark.skip(
        reason="Needs a category assigned to a loan account. No such fixture exists "
               "in SNL_release_monthly, and creating one would mean editing a loan "
               "account. Verify manually or seed the fixture first."
    )
    def test_verify_that_an_assigned_category_uses_the_expected_field_lock_rules(self):
        """TC-LC-068 — Field-lock behaviour when the category is on a loan account."""


class TestLoanCategoryLister:

    def test_verify_that_the_lister_displays_the_expected_column_names(self, category_listing_page, steps):
        """TC-LC-L07 — Lister column headers render properly."""
        steps.append("Read the lister column headers")
        headers = category_listing_page.get_column_headers()
        assert "Name" in headers and "Document sequence" in headers, headers

    @pytest.mark.xfail(
        reason="Bug #43 family — the first column header is the raw key BULK_SELECTED",
        strict=False,
    )
    def test_verify_that_the_lister_column_names_do_not_show_raw_resource_keys(self, category_listing_page, steps):
        """TC-LC-L07a — No raw resource keys appear in the column headers."""
        steps.append("Checked headers for untranslated resource keys")
        headers = category_listing_page.get_column_headers()
        leaked = [h for h in headers if h.startswith("IA.") or h == "BULK_SELECTED"]
        assert not leaked, f"raw keys in headers: {leaked} (all: {headers})"

    def test_verify_that_the_name_filter_returns_only_matching_categories(self, category_listing_page, created_category, steps):
        """TC-LC-L08 — The Name filter narrows the grid to matching rows."""
        listing = category_listing_page
        listing.navigate_to_list()
        steps.append(f"Filtered the Name column by {created_category}")
        listing.search_by_name(created_category)
        rows = listing.row_names()
        listing.clear_search()
        assert rows == [created_category], f"filter returned {rows}"

    def test_verify_that_the_lister_displays_category_data_under_the_correct_columns(
        self, category_listing_page, created_category, steps
    ):
        """TC-LC-L09 — The grid renders records under its columns."""
        listing = category_listing_page
        listing.navigate_to_list()
        listing.search_by_name(created_category)
        steps.append("Checked the grid renders the seeded record")
        assert created_category in listing.row_names()
        assert {"Name", "Document sequence"} <= set(listing.get_column_headers())
