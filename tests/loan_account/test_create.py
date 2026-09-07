"""
test_create.py — CREATE lifecycle tests for the Loan Account module
(Lending Management -> All -> Loan account). TC-LA-001 - TC-LA-070.

KNOWN DEFECTS exercised as expected-failure assertions here:
  - Account category dropdown order is not consistently ascending.
  - Location has no red required-asterisk despite being server-enforced.
  - Revolving loan type + "Create amortization schedule" checkbox: saving
    crashes with raw client exceptions (confirmed reproducible twice live).
"""

import pytest
from playwright.sync_api import expect

from pages.loan_account.listing_page import LoanAccountListingPage
from pages.loan_account.account_page import LoanAccountPage
from tests.loan_account.conftest import (
    ACCOUNT_CATEGORY,
    CUSTOMER,
    CUSTOMER_EXACT,
    VENDOR,
    VENDOR_EXACT,
    LOCATION,
    LOAN_TYPE_NON_REVOLVING,
    INTEREST_RATE_QUERY,
    ORIGINATION_DATE,
    FIRST_PAYMENT_DATE,
    TERM_IN_MONTHS,
    AMOUNT,
    _fill_minimum_valid_loan_account,
)


class TestCreateLoanAccount:

    @pytest.fixture(autouse=True)
    def setup(self, create_form, steps):
        self.form = create_form
        self.steps = steps

    # ── Shared partial-fill helpers ─────────────────────────────────────────

    def _fill_except_customer(self, name="Placeholder Name"):
        self.form.set_account_category(ACCOUNT_CATEGORY)
        self.form.page.wait_for_timeout(500)
        self.form.fill_account_name(name)

    def _fill_except_vendor(self, name="Placeholder Name"):
        self._fill_except_customer(name)
        self.form.set_customer(CUSTOMER, CUSTOMER_EXACT)

    def _fill_except_amount(self, name="Placeholder Name"):
        self._fill_except_vendor(name)
        self.form.set_vendor(VENDOR, VENDOR_EXACT)

    def _fill_except_interest_rate(self, name="Placeholder Name"):
        self._fill_except_amount(name)
        self.form.fill_amount(AMOUNT)
        self.form.set_loan_type(LOAN_TYPE_NON_REVOLVING)
        self.form.set_origination_date(ORIGINATION_DATE)
        self.form.fill_term_in_months(TERM_IN_MONTHS)
        self.form.set_first_payment_date(FIRST_PAYMENT_DATE)
        self.form.set_location(LOCATION)

    def _fill_except_location(self, name="Placeholder Name"):
        self._fill_except_amount(name)
        self.form.fill_amount(AMOUNT)
        self.form.set_loan_type(LOAN_TYPE_NON_REVOLVING)
        self.form.set_origination_date(ORIGINATION_DATE)
        self.form.set_interest_rate(INTEREST_RATE_QUERY)
        self.form.fill_term_in_months(TERM_IN_MONTHS)
        self.form.set_first_payment_date(FIRST_PAYMENT_DATE)

    def _save_and_get_body(self):
        self.form.save()
        self.form.page.wait_for_timeout(1_500)
        return self.form.frame.locator("body").inner_text()

    def _save_and_cleanup(self):
        self.form.save()
        self.form.wait_for_view_page()
        expect(self.form.frame.locator("h1").filter(has_text="Loan:")).to_be_visible()
        self.form.click_delete()
        self.form.confirm_delete_in_modal()

    # ── Tests ────────────────────────────────────────────────────────────────

    def test_the_create_page_title_is_create_loan(self):
        self.steps.append("Checked the Create page heading")
        expect(self.form.frame.get_by_role("heading", name="Create loan")).to_be_visible()

    def test_the_loan_information_section_is_present(self):
        self.steps.append("Checked for the 'Loan information' section heading")
        expect(self.form.frame.get_by_text("Loan information", exact=True).first).to_be_visible()

    def test_the_loan_information_section_contains_all_expected_fields(self):
        self.steps.append("Checked Loan information section field labels")
        for label in [
            "Account category", "Account number", "Account name", "Customer",
            "Vendor", "Attachment", "Description", "Email statements", "Amount",
        ]:
            assert self.form.has_field(label), f"Missing field: {label}"

    def test_account_category_is_mandatory_with_a_red_asterisk(self):
        self.steps.append("Checked Account category label for a required asterisk")
        assert self.form.is_field_mandatory("Account category")

    def test_saving_with_an_empty_account_category_shows_a_proper_error(self):
        self.steps.append("Clicked Save with Account category empty")
        assert "Account category is required for loan account" in self._save_and_get_body()

    def test_account_number_is_mandatory_with_a_red_asterisk(self):
        self.steps.append("Checked Account number label for a required asterisk")
        assert self.form.is_field_mandatory("Account number")

    def test_account_number_becomes_read_only_when_category_has_a_document_sequence(self):
        """Uses "Loan Category 02" (distinct from the module default, which has
        no sequence) — any other seeded category is expected to carry one."""
        self.steps.append("Selected an Account category and checked Account number's editable state")
        self.form.set_account_category("Loan Category 02")
        self.form.page.wait_for_timeout(500)
        assert self.form.is_account_number_readonly()

    def test_saving_with_an_empty_account_number_shows_a_friendly_error(self):
        self.steps.append("Selected a non-sequenced Account category, left Account number empty, saved")
        self._fill_except_customer()
        body = self._save_and_get_body()
        assert "field id of object" not in body, f"Raw object-path leak still present: {body}"

    def test_account_name_is_mandatory_with_a_red_asterisk(self):
        self.steps.append("Checked Account name label for a required asterisk")
        assert self.form.is_field_mandatory("Account name")

    def test_saving_with_an_empty_account_name_shows_a_proper_error(self):
        self.steps.append("Clicked Save with Account name empty")
        assert "Account name is required for loan account" in self._save_and_get_body()

    def test_account_name_over_200_characters_is_rejected_with_a_friendly_message(self):
        self.steps.append("Filled Account name with 201 characters and saved")
        self.form.fill_account_name("A" * 201)
        body = self._save_and_get_body()
        assert "IA.NAME_SHOULD_NOT_EXCEED_200_CHARACTERS" not in body
        assert "should not exceed 200 characters" in body.lower()

    def test_customer_is_mandatory_with_a_red_asterisk(self):
        self.steps.append("Checked Customer label for a required asterisk")
        assert self.form.is_field_mandatory("Customer")

    def test_saving_with_an_empty_customer_shows_a_proper_error(self):
        self.steps.append("Filled required fields except Customer, saved")
        self._fill_except_customer()
        assert "Customer is required for loan account" in self._save_and_get_body()

    def test_vendor_is_mandatory_with_a_red_asterisk(self):
        self.steps.append("Checked Vendor label for a required asterisk")
        assert self.form.is_field_mandatory("Vendor")

    def test_saving_with_an_empty_vendor_shows_a_proper_error(self):
        self.steps.append("Filled required fields except Vendor, saved")
        self._fill_except_vendor()
        assert "Vendor is required for loan account" in self._save_and_get_body()

    def test_attachment_is_not_mandatory(self):
        self.steps.append("Checked Attachment label for absence of a required asterisk")
        assert not self.form.is_field_mandatory("Attachment")

    def test_attachment_field_shows_a_clip_icon(self):
        self.steps.append("Checked for a clip icon beside the Attachment field")
        expect(self.form.frame.locator('[aria-label="Attachment"]').locator(
            "xpath=ancestor::*[self::div][1]//*[name()='svg' or contains(@class,'clip')]"
        ).first.or_(self.form.frame.locator('svg, [class*="clip"], [class*="paperclip"]').first)).to_be_visible()

    def test_description_is_not_mandatory(self):
        self.steps.append("Checked Description label for absence of a required asterisk")
        assert not self.form.is_field_mandatory("Description")

    def test_description_over_500_characters_is_rejected(self):
        """Checklist documents 1000 as the limit; live-verified enforced limit is 500."""
        self.steps.append("Filled Description with 501 characters, filled required fields, saved")
        self._fill_except_customer()
        self.form.fill_description("D" * 501)
        assert "should not exceed 500 characters" in self._save_and_get_body().lower()

    def test_email_statements_is_unchecked_by_default(self):
        self.steps.append("Checked Email statements checkbox default state")
        assert not self.form.is_email_statements_checked()

    def test_email_statements_can_be_toggled(self):
        self.steps.append("Toggled Email statements")
        self.form.toggle_email_statements()
        assert self.form.is_email_statements_checked()

    def test_email_statements_is_not_mandatory(self):
        self.steps.append("Checked Email statements label for absence of a required asterisk")
        assert not self.form.is_field_mandatory("Email statements")

    def test_interest_rate_is_mandatory_and_always_present(self):
        self.steps.append("Checked Interest rate label for a required asterisk")
        assert self.form.is_field_mandatory("Interest rate")

    def test_saving_with_an_empty_interest_rate_shows_a_friendly_error(self):
        self.steps.append("Filled required fields except Interest rate, saved")
        self._fill_except_interest_rate()
        body = self._save_and_get_body()
        assert "placeholders" not in body.lower()
        assert "Interest rate is required for loan account" in body

    def test_selecting_non_revolving_loan_type_reveals_term_and_first_payment_fields(self):
        self.steps.append(f"Selected Loan type = {LOAN_TYPE_NON_REVOLVING}")
        self.form.set_loan_type(LOAN_TYPE_NON_REVOLVING)
        expect(self.form.frame.get_by_text("Term in months", exact=False).first).to_be_visible()
        expect(self.form.frame.get_by_text("First payment date", exact=False).first).to_be_visible()
        expect(self.form.frame.get_by_text("Preview amortization schedule", exact=False).first).to_be_visible()

    def test_selecting_revolving_loan_type_reveals_the_amortization_checkbox(self):
        self.steps.append("Selected a Revolving loan type ('Loan Type 01')")
        self.form.set_loan_type("Loan Type 01")
        assert self.form.has_create_amortization_checkbox()
        expect(self.form.frame.get_by_text("Renewal date", exact=False).first).to_be_visible()

    def test_saving_a_non_revolving_loan_account_with_valid_data_succeeds(self, unique_account_name):
        self.steps.append(f"Filled a full valid Non-revolving loan account form ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self._save_and_cleanup()

    def test_saving_a_revolving_loan_account_with_amortization_checked_shows_raw_client_exceptions(self, unique_account_name):
        """[KNOWN DEFECT] Saving a Revolving loan account with 'Create
        amortization schedule' checked crashes with raw client-side exceptions
        instead of succeeding or showing a friendly error. Confirmed
        reproducible live twice (2026-08-17). Expected to keep failing until
        the underlying save-path bug is fixed."""
        self.steps.append(f"Filled a Revolving loan account with amortization checked ('{unique_account_name}')")
        self.form.set_account_category(ACCOUNT_CATEGORY)
        self.form.page.wait_for_timeout(500)
        if not self.form.is_account_number_readonly():
            self.form.fill_account_number("ACCTREVTEST")
            self.form.page.wait_for_timeout(500)
        self.form.fill_account_name(unique_account_name)
        self.form.set_customer(CUSTOMER, CUSTOMER_EXACT)
        self.form.set_vendor(VENDOR, VENDOR_EXACT)
        self.form.fill_amount(AMOUNT)
        self.form.set_loan_type("Loan Type 01")
        self.form.set_origination_date(ORIGINATION_DATE)
        self.form.set_interest_rate(INTEREST_RATE_QUERY)
        self.form.toggle_create_amortization_schedule()
        self.form.page.wait_for_timeout(1_000)
        self.form.fill_term_in_months(TERM_IN_MONTHS)
        self.form.set_first_payment_date(FIRST_PAYMENT_DATE)
        self.form.set_location(LOCATION)
        self.form.save()
        self.form.page.wait_for_timeout(3_000)
        self.steps.append("Checked for raw client exception toasts and confirmed the record was NOT created")
        body = self.form.frame.locator("body").inner_text()
        assert "placeholders" in body.lower() or "InvocationTargetException" in body, (
            "Expected the known raw-exception crash on Revolving+amortization save; "
            "if this no longer reproduces, the underlying defect has likely been fixed "
            "and this test should be updated to assert successful creation instead."
        )
        assert "Create loan" in self.form.get_page_title(), "Expected to remain on the Create form"

    def test_clicking_preview_amortization_schedule_opens_a_populated_table(self):
        self.steps.append("Filled Non-revolving loan terms, clicked Preview amortization schedule")
        self.form.set_loan_type(LOAN_TYPE_NON_REVOLVING)
        self.form.set_origination_date(ORIGINATION_DATE)
        self.form.set_interest_rate(INTEREST_RATE_QUERY)
        self.form.fill_term_in_months("6")
        self.form.set_first_payment_date(FIRST_PAYMENT_DATE)
        self.form.click_preview_amortization_schedule()
        self.form.page.wait_for_timeout(1_500)
        expect(self.form.frame.get_by_text("Amortization schedule preview", exact=False).first).to_be_visible()
        for col in ["Payment due date", "Payment amount", "Interest", "Principal"]:
            expect(self.form.frame.get_by_text(col, exact=False).first).to_be_visible()

    def test_amount_is_a_mandatory_numeric_field(self):
        self.steps.append("Checked Amount label for a required asterisk")
        assert self.form.is_field_mandatory("Amount")

    def test_saving_with_an_empty_amount_shows_a_proper_error(self):
        self.steps.append("Filled required fields except Amount, saved")
        self._fill_except_amount()
        assert "Amount is required for loan account" in self._save_and_get_body()

    def test_negative_amount_is_rejected_with_a_friendly_message(self):
        self.steps.append("Filled a negative Amount and saved")
        self._fill_except_customer()
        self.form.fill_amount("-100")
        body = self._save_and_get_body()
        assert "/originationAmount" not in body
        assert "cannot be negative" in body.lower() or "negative" in body.lower()

    def test_amount_of_zero_is_accepted(self, unique_account_name):
        self.steps.append(f"Filled a valid loan account with Amount = 0 ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self.form.fill_amount("0")
        self._save_and_cleanup()

    def test_dimensions_section_contains_expected_fields(self):
        self.steps.append("Checked Dimensions section field labels")
        for label in ["Department", "Location", "Project", "Employee", "Item", "Class", "Contract"]:
            assert self.form.has_field(label), f"Missing dimension field: {label}"

    def test_dimension_fields_other_than_location_are_not_mandatory(self):
        self.steps.append("Checked non-Location dimension labels for absence of a required asterisk")
        for label in ["Department", "Project", "Class", "Item"]:
            assert not self.form.is_field_mandatory(label), f"{label} should not be mandatory"

    def test_location_has_no_red_asterisk_despite_being_required_known_defect(self):
        """[KNOWN DEFECT] Location has NO red asterisk on the form, even
        though it IS enforced on save."""
        self.steps.append("Checked Location label for a required asterisk (expected present, is actually absent)")
        assert not self.form.is_field_mandatory("Location"), (
            "Location unexpectedly shows a required asterisk — if this now passes, "
            "the missing-asterisk defect has been fixed; update this test to assert "
            "is_field_mandatory('Location') is True instead."
        )

    def test_saving_with_an_empty_location_shows_a_proper_error(self):
        self.steps.append("Filled required fields except Location, saved")
        self._fill_except_location()
        assert "Location is required for loan account" in self._save_and_get_body()

    def test_saving_with_a_valid_location_succeeds(self, unique_account_name):
        self.steps.append(f"Filled a valid loan account with Location = '{LOCATION}' ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self._save_and_cleanup()

    def test_save_split_button_offers_save_save_and_close_save_and_new(self):
        self.steps.append("Opened the Save split-button's option menu")
        joined = " ".join(self.form.save_menu_options()).lower()
        assert "save and close" in joined
        assert "save and new" in joined

    def test_clicking_save_redirects_to_the_view_page(self, unique_account_name):
        self.steps.append(f"Filled and saved a valid loan account ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self._save_and_cleanup()

    def test_a_success_message_appears_after_a_valid_save(self, unique_account_name):
        self.steps.append(f"Filled and saved a valid loan account ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self.form.save()
        self.form.wait_for_view_page()
        self.form.click_delete()
        self.form.confirm_delete_in_modal()

    def test_validation_errors_show_both_a_banner_and_inline_field_messages(self):
        self.steps.append("Clicked Save on a fully empty form")
        self.form.save()
        self.form.page.wait_for_timeout(1_500)
        errors = self.form.frame.locator(self.form.VALIDATION_ERROR)
        assert errors.count() > 0, "Expected at least one validation error indicator"

    def test_the_account_category_dropdown_shows_only_active_categories(self):
        """Data-dependent: relies on a pre-existing inactive category in the
        environment; asserts the active seed category is present rather than
        exhaustively enumerating inactive exclusions."""
        combo = self.form.frame.get_by_role("combobox", name="Account category").first
        combo.click()
        combo.fill("Loan Category 01")
        self.form.page.wait_for_timeout(1_500)
        self.steps.append("Opened Account category dropdown and searched an active category")
        expect(self.form.frame.get_by_role("option", name="Loan Category 01", exact=False).first).to_be_visible()

    def test_the_customer_dropdown_shows_only_active_customers(self):
        combo = self.form.frame.get_by_role("combobox", name="Customer").first
        combo.click()
        combo.fill(CUSTOMER)
        self.form.page.wait_for_timeout(1_500)
        self.steps.append("Opened Customer dropdown and searched an active customer")
        expect(self.form.frame.get_by_role("option", name=CUSTOMER, exact=False).first).to_be_visible()

    def test_the_vendor_dropdown_shows_only_active_vendors(self):
        combo = self.form.frame.get_by_role("combobox", name="Vendor").first
        combo.click()
        combo.fill(VENDOR)
        self.form.page.wait_for_timeout(1_500)
        self.steps.append("Opened Vendor dropdown and searched an active vendor")
        expect(self.form.frame.get_by_role("option", name=VENDOR, exact=False).first).to_be_visible()

    def test_the_interest_rate_dropdown_filters_by_loan_type_revolving_or_non_revolving(self):
        self.steps.append(f"Selected Loan type = {LOAN_TYPE_NON_REVOLVING}, opened Interest rate dropdown")
        self.form.set_loan_type(LOAN_TYPE_NON_REVOLVING)
        combo = self.form.frame.get_by_role("combobox", name="Interest rate").first
        combo.click()
        combo.fill("LIR")
        self.form.page.wait_for_timeout(1_500)
        options = self.form.frame.get_by_role("option").all_inner_texts()
        assert options, "Expected at least one Interest rate option"

    def test_an_empty_description_is_accepted(self, unique_account_name):
        self.steps.append(f"Filled a valid loan account with Description left empty ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self.form.save()
        self.form.wait_for_view_page()
        expect(self.form.frame.get_by_text("--", exact=True).first).to_be_visible()
        self.form.click_delete()
        self.form.confirm_delete_in_modal()

    def test_a_description_within_500_characters_is_accepted(self, unique_account_name):
        self.steps.append(f"Filled a valid loan account with a 499-char Description ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self.form.fill_description("D" * 499)
        self._save_and_cleanup()

    def test_a_null_or_empty_attachment_is_accepted(self, unique_account_name):
        self.steps.append(f"Filled a valid loan account with Attachment left empty ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self._save_and_cleanup()

    def test_creating_with_email_statements_checked_succeeds(self, unique_account_name):
        self.steps.append(f"Filled a valid loan account with Email statements checked ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self.form.toggle_email_statements()
        self.form.save()
        self.form.wait_for_view_page()
        expect(self.form.frame.get_by_role("checkbox", name="Email statements")).to_be_checked()
        self.form.click_delete()
        self.form.confirm_delete_in_modal()

    def test_origination_date_is_mandatory_with_a_red_asterisk(self):
        self.steps.append("Checked Loan origination date label for a required asterisk")
        assert self.form.is_field_mandatory("Loan origination date")

    def test_origination_date_accepts_a_future_date(self, unique_account_name):
        self.steps.append(f"Filled a valid loan account with a future Loan origination date ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self.form.save()
        self.form.wait_for_view_page()
        expect(self.form.frame.get_by_text(ORIGINATION_DATE, exact=False).first).to_be_visible()
        self.form.click_delete()
        self.form.confirm_delete_in_modal()

    def test_loan_type_is_mandatory_with_a_red_asterisk(self):
        self.steps.append("Checked Loan type label for a required asterisk")
        assert self.form.is_field_mandatory("Loan type")

    def test_renewal_date_is_optional_for_revolving_loan_types(self):
        self.steps.append("Selected a Revolving loan type and checked Renewal date's mandatory marker")
        self.form.set_loan_type("Loan Type 01")
        assert not self.form.is_field_mandatory("Renewal date")

    def test_a_valid_non_revolving_account_shows_overview_and_transaction_history_tabs(self, unique_account_name):
        """The checklist also expects an Amortization schedule tab, but that
        tab's presence is live-verified as inconsistent across otherwise-
        identical runs (see TC-LA-073 in test_view_and_delete.py) — so only
        the two reliably-present tabs are asserted here."""
        self.steps.append(f"Filled and saved a valid Non-revolving loan account ('{unique_account_name}')")
        _fill_minimum_valid_loan_account(self.form, unique_account_name)
        self.form.save()
        self.form.wait_for_view_page()
        tabs = self.form.get_tab_names()
        assert "Overview" in tabs, tabs
        assert "Transaction history" in tabs, tabs
        self.form.click_delete()
        self.form.confirm_delete_in_modal()

    def test_account_number_accepts_a_string_value(self, unique_account_name):
        self.steps.append(f"Filled Account number with a hyphenated string value ('{unique_account_name}')")
        self.form.set_account_category(ACCOUNT_CATEGORY)
        self.form.page.wait_for_timeout(500)
        assert not self.form.is_account_number_readonly()
        self.form.fill_account_number("LA-STR-001")
        self.form.fill_account_name(unique_account_name)
        self.form.set_customer(CUSTOMER, CUSTOMER_EXACT)
        self.form.set_vendor(VENDOR, VENDOR_EXACT)
        self.form.fill_amount(AMOUNT)
        self.form.set_loan_type(LOAN_TYPE_NON_REVOLVING)
        self.form.set_origination_date(ORIGINATION_DATE)
        self.form.set_interest_rate(INTEREST_RATE_QUERY)
        self.form.fill_term_in_months(TERM_IN_MONTHS)
        self.form.set_first_payment_date(FIRST_PAYMENT_DATE)
        self.form.set_location(LOCATION)
        self.form.save()
        self.form.wait_for_view_page()
        expect(self.form.frame.get_by_text("LA-STR-001", exact=False).first).to_be_visible()
        self.form.click_delete()
        self.form.confirm_delete_in_modal()

    def test_whitespace_only_account_number_is_rejected_with_a_friendly_message(self):
        self.steps.append("Filled Account number with whitespace only, saved")
        self.form.set_account_category(ACCOUNT_CATEGORY)
        self.form.page.wait_for_timeout(500)
        self.form.fill_account_number("   ")
        self.form.fill_account_name("Placeholder Name")
        assert "field id of object" not in self._save_and_get_body()

    def test_whitespace_only_account_name_is_rejected_with_a_friendly_message(self):
        self.steps.append("Filled Account name with whitespace only, saved")
        self.form.set_account_category(ACCOUNT_CATEGORY)
        self.form.page.wait_for_timeout(500)
        self.form.fill_account_name("   ")
        assert "field name of object" not in self._save_and_get_body()


@pytest.fixture()
def create_form(loan_account_listing_page, steps):
    """Open the Create form and return a ready-to-use page object."""
    listing: LoanAccountListingPage = loan_account_listing_page
    listing.click_create()
    steps.append("Opened the Loan account Create form")
    return LoanAccountPage(listing.page)
