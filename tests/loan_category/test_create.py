"""
test_create.py
=========================
Playwright / pytest tests for the CREATE stage of the Loan account category
module (Lending Management → Setup → Loan account categories).

Checklist rows: TC-LC-001 – TC-LC-029 ("Loan Category - CRUD", SL 1-29).
Verified live against release www-p303 / SNL_release_monthly / LME entity
on 2026-08-17.

Two checklist rows are asserted against observed behaviour rather than their
stated wording, with the discrepancy called out in the test:
  * SL 13/14 say Description is capped at 1000 characters. The app enforces
    500 (501 rejected), matching SL 11's "within 500 characters".
  * SL 20 and SL 29 are API/DB-level and are skipped with a reason — they are
    not reachable through the UI.
"""

import pytest

from pages.loan_category.category_page import LoanCategoryPage
from .conftest import DESCRIPTION_MAX, NAME_MAX, OBJECT_PATH, delete_if_present


class TestCreateLoanCategory:

    # ── Page structure (SL 1-3) ────────────────────────────────────────────────

    def test_verify_that_the_create_page_title_is_create_loan_account_category(self, create_form, steps):
        """TC-LC-001 — Create page title is "Create loan account category"."""
        steps.append("Read the create page H1")
        assert create_form.get_page_title() == "Create loan account category"

    def test_verify_that_the_create_form_shows_all_category_information_fields(self, create_form, steps):
        """TC-LC-002 — The create form shows the category information fields."""
        steps.append("Read the field labels on the create form")
        labels = [l.rstrip(" *").strip() for l in create_form.field_labels()]
        for expected in ("Name", "Document sequence", "Description"):
            assert expected in labels, f"{expected!r} missing from {labels}"

    def test_verify_that_the_name_field_is_marked_as_required(self, create_form, steps):
        """TC-LC-003 — Name is mandatory (red asterisk)."""
        steps.append("Checked the Name mandatory marker")
        assert create_form.is_field_mandatory("Name")

    # ── Name field (SL 4-9) ────────────────────────────────────────────────────

    def test_verify_that_a_category_can_be_created_with_a_valid_name(
        self, category_listing_page, unique_category_name, steps
    ):
        """TC-LC-004 — A record is created with a valid name."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append("Saved a category with only a name")
        cp.save()
        try:
            cp.wait_for_view_page()
            assert unique_category_name in cp.view_field_text("Name")
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_the_name_field_accepts_200_characters(
        self, category_listing_page, steps
    ):
        """TC-LC-005 — Name accepts the documented 200-character maximum."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        name = "N" * NAME_MAX
        steps.append(f"Entered a {NAME_MAX}-character name and saved")
        cp.fill_name(name)
        cp.save()
        try:
            cp.wait_for_view_page()
            assert len(cp.view_field_text("Name")) >= NAME_MAX
        finally:
            delete_if_present(listing, cp, name)

    @pytest.mark.xfail(
        reason="No maxlength on the Name input and the over-length error leaks the "
               "internal object path (same family as Bug #87)",
        strict=False,
    )
    def test_verify_that_a_name_longer_than_200_characters_is_rejected_readably(self, create_form, steps):
        """TC-LC-006 — Over-200 name is capped or rejected with a readable message."""
        steps.append(f"Entered a {NAME_MAX + 1}-character name")
        assert create_form.get_name_maxlength() is not None, "Name input has no maxlength cap"
        create_form.fill_name("N" * (NAME_MAX + 1))
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert banner, "an over-length name was accepted with no error"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    def test_verify_that_saving_with_a_blank_name_shows_an_error(self, create_form, steps):
        """TC-LC-007 — An empty name is rejected with a proper error."""
        steps.append("Saved with the name left empty")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert banner, "an empty name was accepted with no error"

    @pytest.mark.xfail(
        reason="The whitespace-only name error leaks the internal object path "
               "(same family as Bug #30)",
        strict=False,
    )
    def test_verify_that_saving_with_a_whitespace_only_name_shows_a_readable_error(self, create_form, steps):
        """TC-LC-008 — A whitespace-only name is rejected with a readable message."""
        steps.append("Saved with a whitespace-only name")
        create_form.fill_name("   ")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert banner, "a whitespace-only name was accepted with no error"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    def test_verify_that_a_name_with_control_characters_is_not_silently_saved(self, create_form, steps):
        """
        TC-LC-009 — A name in an invalid format is rejected.

        The app documents no character restriction, so this asserts the
        observable contract: a control-character name must not save silently.
        """
        steps.append("Saved a name containing control characters")
        create_form.fill_name("\t\n")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        title = create_form.get_page_title()
        assert "Create" in title or create_form.error_banner_text(), (
            "a control-character name appears to have saved"
        )

    # ── Description (SL 10-14) ─────────────────────────────────────────────────

    def test_verify_that_the_description_field_is_optional(self, create_form, steps):
        """TC-LC-010 — Description is not mandatory."""
        steps.append("Checked Description has no mandatory marker")
        assert create_form.has_field("Description")
        assert not create_form.is_field_mandatory("Description")

    def test_verify_that_the_description_field_accepts_500_characters(
        self, category_listing_page, unique_category_name, steps
    ):
        """TC-LC-011 — A 500-character description is accepted."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append(f"Entered a {DESCRIPTION_MAX}-character description and saved")
        cp.fill_description("D" * DESCRIPTION_MAX)
        cp.save()
        try:
            cp.wait_for_view_page()
            assert len(cp.view_field_text("Description")) >= DESCRIPTION_MAX
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_a_category_can_be_saved_with_an_empty_description(
        self, category_listing_page, unique_category_name, steps
    ):
        """TC-LC-012 — An empty description is accepted."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append("Saved with Description left empty")
        cp.save()
        try:
            cp.wait_for_view_page()
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_a_description_longer_than_500_characters_is_rejected(self, create_form, steps):
        """
        TC-LC-013 — An over-long description is rejected.

        The checklist says 1000; the app enforces 500 (501 rejected, confirmed
        live 2026-08-17), so the real limit is asserted here.
        """
        steps.append(f"Entered a {DESCRIPTION_MAX + 1}-character description")
        create_form.fill_name("AutoCatDescLen")
        create_form.fill_description("D" * (DESCRIPTION_MAX + 1))
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        assert create_form.error_banner_text(), (
            f"a {DESCRIPTION_MAX + 1}-character description was accepted"
        )

    @pytest.mark.xfail(
        reason="The over-length description error leaks the internal object path "
               "(same family as Bug #87)",
        strict=False,
    )
    def test_verify_that_an_overlength_description_shows_a_readable_error(self, create_form, steps):
        """TC-LC-014 — The over-length description message should be readable."""
        steps.append("Read the over-length description error")
        create_form.fill_name("AutoCatDescMsg")
        create_form.fill_description("D" * (DESCRIPTION_MAX + 1))
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        banner = create_form.error_banner_text()
        assert banner, "no error was shown"
        assert OBJECT_PATH not in banner, f"message leaks the object path: {banner!r}"

    # ── Document sequence (SL 15-20) ───────────────────────────────────────────

    def test_verify_that_the_document_sequence_field_is_optional(self, create_form, steps):
        """TC-LC-016 — Document sequence is not mandatory."""
        steps.append("Checked Document sequence has no mandatory marker")
        assert create_form.has_field("Document sequence")
        assert not create_form.is_field_mandatory("Document sequence")

    def test_verify_that_a_valid_document_sequence_can_be_selected_and_saved(
        self, category_listing_page, unique_category_name, steps
    ):
        """
        TC-LC-015 — A valid document sequence is accepted.

        Document sequence is a picker; if this company defines none, there is
        nothing valid to select and the row cannot be proven here.
        """
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        steps.append("Opened the Document sequence picker")
        options = cp.document_sequence_options()
        if not options:
            pytest.skip(
                "No document sequences are defined in this company, so a valid "
                "value cannot be selected. Seed one to cover this row."
            )
        cp.fill_name(unique_category_name)
        cp.fill_document_sequence(options[0])
        cp.save()
        try:
            cp.wait_for_view_page()
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_a_category_can_be_saved_without_a_document_sequence(
        self, category_listing_page, unique_category_name, steps
    ):
        """TC-LC-016b / TC-LC-019 — A record saves with no document sequence."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append("Saved with Document sequence left empty")
        cp.save()
        try:
            cp.wait_for_view_page()
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_a_document_sequence_cannot_be_reused_by_another_category(
        self, category_listing_page, steps
    ):
        """TC-LC-017 — A document sequence already in use is rejected."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        options = cp.document_sequence_options()
        if not options:
            pytest.skip(
                "No document sequences defined in this company, so reuse cannot "
                "be exercised. Seed one to cover this row."
            )
        first = f"AutoCatSeqA_{options[0][:6]}"
        second = f"AutoCatSeqB_{options[0][:6]}"
        try:
            cp.fill_name(first)
            cp.fill_document_sequence(options[0])
            cp.save()
            cp.wait_for_view_page()

            steps.append("Reused the same document sequence on a second record")
            listing.navigate_to_list()
            listing.click_create()
            cp.fill_name(second)
            cp.fill_document_sequence(options[0])
            cp.save()
            cp.page.wait_for_timeout(2_500)
            assert cp.error_banner_text(), "a reused document sequence was accepted"
        finally:
            for n in (first, second):
                delete_if_present(listing, cp, n)

    def test_verify_that_an_invalid_document_sequence_is_not_silently_saved(self, create_form, steps):
        """TC-LC-018 — An invalid document sequence value is not silently accepted."""
        steps.append("Typed a special-character document sequence without picking an option")
        create_form.fill_name("AutoCatSeqBad")
        create_form.type_document_sequence("!!!@@@###")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        value = create_form.get_document_sequence_value()
        assert create_form.error_banner_text() or value != "!!!@@@###", (
            "an unmatched document sequence value appears to have been accepted"
        )

    @pytest.mark.skip(
        reason="API-level only — a malformed request body for the document sequence "
               "cannot be produced through the UI, where the field is a picker."
    )
    def test_verify_that_a_malformed_document_sequence_request_returns_an_error(self):
        """TC-LC-020 — Malformed document-sequence request returns a proper error."""

    # ── Save behaviour (SL 21-28) ──────────────────────────────────────────────

    def test_verify_that_the_create_action_is_available_from_the_list_page(self, category_listing_page, steps):
        """TC-LC-021 — The Create action is reachable from the list page."""
        steps.append("Checked Create is available on the lister")
        assert category_listing_page.is_create_visible()

    def test_verify_that_the_save_control_is_visible_on_the_create_page(self, create_form, steps):
        """TC-LC-022 — The Save control is visible on the create page."""
        steps.append("Looked for the Save control")
        assert create_form.frame.locator(
            '[aria-label="Save"], [role=menuitem]:has-text("Save")'
        ).count() > 0

    def test_verify_that_the_save_menu_contains_all_expected_options(self, create_form, steps):
        """TC-LC-023 — Save offers Save / Save and new / Save and close."""
        steps.append("Opened the Save split-button menu")
        opts = [o.lower() for o in create_form.save_menu_options()]
        for wanted in ("save", "save and close", "save and new"):
            assert any(o == wanted for o in opts), f"{wanted!r} missing from {opts}"

    def test_verify_that_save_creates_the_category_and_opens_its_detail_page(
        self, category_listing_page, unique_category_name, steps
    ):
        """TC-LC-024 — Save stores the record and opens its detail page."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append("Clicked Save")
        cp.save()
        try:
            cp.wait_for_view_page()
            assert cp.VIEW_HEADING_PREFIX in cp.get_page_title()
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_save_and_new_creates_the_category_and_opens_a_blank_form(
        self, category_listing_page, unique_category_name, steps
    ):
        """TC-LC-025 — "Save and new" stores the record and resets the form."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append("Saved using 'Save and new'")
        cp.save_via("Save and new")
        cp.page.wait_for_timeout(2_500)
        try:
            listing.navigate_to_list()
            listing.search_by_name(unique_category_name)
            assert listing.is_record_visible(unique_category_name), "record was not saved"
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_save_and_close_creates_the_category_and_returns_to_the_list(
        self, category_listing_page, unique_category_name, steps
    ):
        """TC-LC-026 — "Save and close" stores the record and returns to the list."""
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append("Saved using 'Save and close'")
        cp.save_via("Save and close")
        cp.page.wait_for_timeout(2_500)
        try:
            listing.wait_for_list_page()
            listing.search_by_name(unique_category_name)
            assert listing.is_record_visible(unique_category_name)
        finally:
            delete_if_present(listing, cp, unique_category_name)

    def test_verify_that_saving_an_invalid_form_shows_validation_errors(self, create_form, steps):
        """TC-LC-027 — Validation errors appear when a save option is used."""
        steps.append("Saved an empty form")
        create_form.save()
        create_form.page.wait_for_timeout(2_000)
        assert create_form.error_banner_text() or create_form.has_inline_field_error()

    def test_verify_that_creating_a_category_shows_a_confirmation_message(
        self, category_listing_page, unique_category_name, steps
    ):
        """
        TC-LC-028 — Creating a category shows a confirmation message.

        The toast is short-lived, so recording is armed before Save; reading
        after the redirect would miss it and look like no message at all.
        """
        listing = category_listing_page
        listing.click_create()
        cp = LoanCategoryPage(listing.page)
        cp.fill_name(unique_category_name)
        steps.append("Armed the toast recorder, then saved")
        cp.start_recording_toasts()
        cp.save()
        toast = cp.wait_for_toast()
        try:
            assert toast, "no confirmation message was shown after creating a category"
            steps.append(f"Confirmation message: {toast!r}")
        finally:
            delete_if_present(listing, cp, unique_category_name)

    @pytest.mark.skip(
        reason="Database-level — verifying the SNLLOANCATEGORY row needs a direct "
               "Oracle query (integrations/db.py), not the UI."
    )
    def test_verify_that_creating_a_category_adds_a_valid_snlloancategory_record(self):
        """TC-LC-029 — A proper entry is created in SNLLOANCATEGORY."""
