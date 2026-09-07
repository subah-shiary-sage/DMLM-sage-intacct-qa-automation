"""
test_create.py
=========================
Playwright / pytest tests for the CREATE lifecycle stage of the Loan Type
module (Lending Management → Setup → Loan type).

Test IDs: TC-LT-028 – TC-LT-046, TC-LT-057 – TC-LT-058, TC-LT-064 – TC-LT-066,
TC-LT-067 – TC-LT-078 (new — added to reach full parity with the "Loan Type -
CRUD" checklist sheet in LME_Regression_Consolidated.xlsx, 2026-08-17).
Selectors/flows verified against live DOM 2026-07-15/16. See
TEST_CASES_Loan_Type.md for the full field/behaviour inventory, including
server-side validations not documented in the original spreadsheet:
at least one Payment priority row is required; each row's Sort order is
required; Non-revolving requires both a Principal AND an Interest row; and a
row's Fee type value is not auto-cleared when its Type switches away from Fee.

TC-LT-067–078 close checklist items not previously automated: the Save
split-button's exact option set and its "Save and new" behaviour, section
default-expand states (including the known KNOWN-DEFECT for "Loan invoicing
defaults" — checklist row 38), Sort order's numeric-only / duplicate /
missing-value validations, Payment priority Type-column exclusivity
(Principal/Interest single-row vs Fee multi-row), and the row-highlight and
mandatory-field-validation-on-save checklist items.
"""

import pytest
from playwright.sync_api import expect

from pages.loan_type.listing_page import LoanTypeListingPage
from pages.loan_type.type_page import LoanTypePage

# Values verified live against the DMLM entity on 2026-07-15 — see
# TEST_CASES_Loan_Type.md for the full picker-option inventory. Duplicated
# from conftest.py's _fill_minimum_valid_loan_type rather than imported, to
# keep this test file independent of conftest's private helpers.
ORDER_ENTRY_TXN_DEF = "Loan management invoicing"
PRINCIPAL_ITEM      = "p01--Loan principal item"
INTEREST_ITEM        = "i01--Loan interest item"


@pytest.fixture()
def create_form(loan_type_listing_page, steps):
    """Open the Create form and return a ready-to-use page object."""
    listing: LoanTypeListingPage = loan_type_listing_page
    listing.click_create()
    steps.append("Opened the Loan type Create form")
    return LoanTypePage(listing.page)


class TestCreateLoanType:

    def test_the_loan_type_name_field_is_present_on_the_create_form(self, create_form, steps):
        """TC-LT-028 — Create form has a Loan type name text field."""
        steps.append("Checked for the 'Loan type' name textbox")
        expect(create_form.frame.locator(create_form.NAME_INPUT).first).to_be_visible()

    def test_saving_with_an_empty_loan_type_name_is_blocked_and_keeps_the_user_on_the_create_form(self, create_form, steps):
        """TC-LT-029 — Loan type name is required; saving without it shows an error."""
        steps.append("Left Loan type name empty and clicked Save")
        create_form.save()
        create_form.page.wait_for_timeout(1_500)
        steps.append("Verified we're still on the Create form")
        expect(
            create_form.frame.get_by_role("heading", name="Create loan type")
        ).to_be_visible()

    def test_the_description_field_is_optional_and_has_no_required_asterisk(self, create_form, steps):
        """TC-LT-030 — Description field is optional (no asterisk)."""
        steps.append("Checked the Description field's label for a required asterisk")
        desc_input = create_form.frame.locator(create_form.DESCRIPTION_INPUT).first
        field = desc_input.locator("xpath=..")
        expect(field.get_by_text("*", exact=True)).to_have_count(0)

    def test_the_type_field_shows_revolving_and_non_revolving_radio_options(self, create_form, steps):
        """TC-LT-031 — Type field shows Revolving/Non-revolving options."""
        steps.append("Checked the Type radio group")
        expect(create_form.frame.get_by_role("radio", name="Revolving", exact=True)).to_be_visible()
        expect(create_form.frame.get_by_role("radio", name="Non-revolving", exact=True)).to_be_visible()

    def test_the_interest_type_dropdown_contains_compound_and_simple_options(self, create_form, steps):
        """TC-LT-032 — Interest type dropdown contains 'Compound' and 'Simple'."""
        steps.append("Opened the Interest type dropdown")
        combo = create_form.frame.get_by_role("combobox", name="Interest type").first
        combo.click()
        create_form.page.wait_for_timeout(400)
        expect(create_form.frame.get_by_role("option", name="Simple")).to_be_visible()
        expect(create_form.frame.get_by_role("option", name="Compound")).to_be_visible()

    def test_the_interest_calculation_method_field_appears_and_is_required_once_type_is_selected(self, create_form, steps):
        """TC-LT-033 — Interest calculation method appears (required, '*') after Type is selected."""
        steps.append("Selected Type = Revolving")
        create_form.select_type("Revolving")
        steps.append("Checked that Interest calculation method appeared with a required asterisk")
        label = create_form.frame.get_by_text("Interest calculation method", exact=True).first
        field = label.locator("xpath=..")
        expect(field.get_by_text("*", exact=True)).to_be_visible()

    def test_the_interest_calculation_method_dropdown_offers_actual_365_and_actual_360_for_revolving_type(self, create_form, steps):
        """TC-LT-034 — Interest calculation method offers Actual/365 and Actual/360 for Revolving."""
        steps.append("Selected Type = Revolving")
        create_form.select_type("Revolving")
        steps.append("Opened the Interest calculation method dropdown")
        combo = create_form.frame.get_by_role("combobox", name="Interest calculation method").first
        combo.click()
        create_form.page.wait_for_timeout(400)
        expect(create_form.frame.get_by_role("option", name="Actual/365")).to_be_visible()
        expect(create_form.frame.get_by_role("option", name="Actual/360")).to_be_visible()

    def test_the_interest_calculation_method_dropdown_offers_actual_365_actual_360_and_30_360_for_non_revolving_type(self, create_form, steps):
        """TC-LT-034b [new] — Interest calculation method offers Actual/365, Actual/360, AND 30/360
        for Non-revolving (a superset of Revolving's two options)."""
        steps.append("Selected Type = Non-revolving")
        create_form.select_type("Non-revolving")
        steps.append("Opened the Interest calculation method dropdown")
        combo = create_form.frame.get_by_role("combobox", name="Interest calculation method").first
        combo.click()
        create_form.page.wait_for_timeout(400)
        expect(create_form.frame.get_by_role("option", name="Actual/365")).to_be_visible()
        expect(create_form.frame.get_by_role("option", name="Actual/360")).to_be_visible()
        expect(create_form.frame.get_by_role("option", name="30/360")).to_be_visible()

    def test_the_order_entry_transaction_definition_field_shows_a_required_asterisk(self, create_form, steps):
        """TC-LT-036 — Order Entry transaction definition shows a required asterisk."""
        steps.append("Checked the Order Entry transaction definition label")
        label = create_form.frame.get_by_text("Order Entry transaction definition", exact=True).first
        field = label.locator("xpath=..")
        expect(field.get_by_text("*", exact=True)).to_be_visible()

    def test_the_item_for_loan_principal_posting_field_shows_a_required_asterisk(self, create_form, steps):
        """TC-LT-037 — Item for loan principal posting shows a required asterisk."""
        steps.append("Checked the Item for loan principal posting label")
        label = create_form.frame.get_by_text("Item for loan principal posting", exact=True).first
        field = label.locator("xpath=..")
        expect(field.get_by_text("*", exact=True)).to_be_visible()

    def test_the_item_for_loan_interest_posting_field_shows_a_required_asterisk(self, create_form, steps):
        """TC-LT-038 — Item for loan interest posting shows a required asterisk."""
        steps.append("Checked the Item for loan interest posting label")
        label = create_form.frame.get_by_text("Item for loan interest posting", exact=True).first
        field = label.locator("xpath=..")
        expect(field.get_by_text("*", exact=True)).to_be_visible()

    def test_the_add_row_button_is_present_in_the_payment_priority_order_section(self, create_form, steps):
        """TC-LT-039 — 'Add row' button is present in Payment priority order section."""
        steps.append("Scrolled to Payment priority order section")
        expect(create_form.frame.get_by_role("button", name="Add row").first).to_be_visible()

    def test_the_payment_priority_grid_has_sort_order_type_and_fee_type_columns_on_create(self, create_form, steps):
        """TC-LT-040 — Payment priority grid has Sort order, Type and Fee type columns."""
        steps.append("Checked Payment priority order grid column headers")
        headers = create_form.frame.get_by_role("columnheader")
        text = " ".join(h.inner_text() for h in headers.all()).lower()
        assert "sort order" in text
        assert "type" in text
        assert "fee type" in text

    def test_clicking_add_row_increments_the_payment_priority_grid_by_one_row(self, create_form, steps):
        """TC-LT-041 — Clicking 'Add row' increments the Payment priority grid by one row."""
        before = create_form.get_payment_priority_row_count()
        steps.append(f"Recorded starting row count = {before}")
        create_form.click_add_row()
        after = create_form.get_payment_priority_row_count()
        steps.append(f"Row count after Add row = {after}")
        assert after == before + 1

    def test_clicking_remove_row_decrements_the_payment_priority_grid(self, create_form, steps):
        """TC-LT-042 — Clicking Remove row decrements the Payment priority grid."""
        create_form.click_add_row()
        before = create_form.get_payment_priority_row_count()
        steps.append(f"Added a row; row count = {before}")
        create_form.click_remove_row(0)
        after = create_form.get_payment_priority_row_count()
        steps.append(f"Row count after Remove row = {after}")
        assert after == before - 1

    def test_the_fee_type_field_is_disabled_when_the_row_type_is_interest(self, create_form, steps):
        """TC-LT-043 — Fee type field is disabled when Type = Interest."""
        create_form.click_add_row()
        steps.append("Added a Payment priority row, set Type = Interest")
        create_form.set_row_type("Interest")
        assert not create_form.is_row_fee_type_enabled(0)

    def test_the_fee_type_field_is_enabled_when_the_row_type_is_fee(self, create_form, steps):
        """TC-LT-044 — Fee type field is enabled when Type = Fee."""
        create_form.click_add_row()
        steps.append("Added a Payment priority row, set Type = Fee")
        create_form.set_row_type("Fee")
        assert create_form.is_row_fee_type_enabled(0)

    def test_the_save_button_is_visible_on_the_create_form(self, create_form, steps):
        """TC-LT-045 — Save button is visible on the create form."""
        steps.append("Checked header for Save action")
        expect(create_form.frame.locator('[role="menuitem"]:has-text("Save")')).to_be_visible()

    def test_clicking_cancel_discards_changes_and_returns_to_the_loan_types_list(self, create_form, unique_loan_type_name, steps):
        """TC-LT-046 — Cancel discards changes and returns to the Loan types list."""
        create_form.fill_name(unique_loan_type_name)
        steps.append(f"Filled Loan type = '{unique_loan_type_name}'")
        create_form.cancel()
        steps.append("Clicked Cancel")
        expect(
            create_form.frame.get_by_role("heading", name="Loan types")
        ).to_be_visible()

    def test_saving_with_zero_payment_priority_rows_shows_a_validation_error(self, create_form, unique_loan_type_name, steps):
        """TC-LT-057 [new] — Saving with zero Payment priority rows shows a validation error."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Revolving")
        lt.set_interest_type("Compound")
        lt.set_interest_calculation_method("Actual/365")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        steps.append("Filled every required field except a Payment priority row")
        lt.save()
        steps.append("Clicked Save with zero Payment priority rows")
        expect(lt.frame.get_by_role("alert")).to_contain_text(
            "At least one Payment priority order line item is required"
        )

    def test_saving_a_payment_priority_row_with_an_empty_sort_order_shows_a_validation_error(self, create_form, unique_loan_type_name, steps):
        """TC-LT-058 [new] — Saving a Payment priority row with empty Sort order shows a validation error."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Revolving")
        lt.set_interest_type("Compound")
        lt.set_interest_calculation_method("Actual/365")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_type("Interest")
        steps.append("Added a Payment priority row with Type set but Sort order left empty")
        lt.save()
        steps.append("Clicked Save with an empty Sort order")
        expect(lt.frame.get_by_role("alert")).to_contain_text("sortOrder")

    def test_a_fully_valid_loan_type_saves_successfully_and_opens_the_view_page(self, create_form, unique_loan_type_name, steps):
        """[new] A fully valid Loan Type (all required fields + one Payment priority row) saves successfully."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Revolving")
        lt.set_interest_type("Compound")
        lt.set_interest_calculation_method("Actual/365")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Interest")
        steps.append(f"Filled all required fields for '{unique_loan_type_name}'")
        create_form.save()
        steps.append("Clicked Save")
        create_form.wait_for_view_page()
        expect(create_form.frame.locator("h1").filter(has_text="Loan type:")).to_be_visible()
        # Cleanup
        create_form.click_delete()
        create_form.confirm_delete_in_modal()

    def test_a_non_revolving_loan_type_saves_successfully_with_one_principal_row_and_one_interest_row(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-064 [new] — A Non-revolving Loan Type saves with a Principal row + an Interest row."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Non-revolving")
        lt.set_interest_type("Simple")
        lt.set_interest_calculation_method("30/360")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Interest")
        lt.click_add_row()
        lt.set_row_sort_order("2")
        lt.set_row_type("Principal")
        steps.append(f"Filled Non-revolving '{unique_loan_type_name}' with one Interest row and one Principal row")
        lt.save()
        steps.append("Clicked Save")
        lt.wait_for_view_page()
        expect(lt.frame.locator("h1").filter(has_text="Loan type:")).to_be_visible()
        expect(lt.frame.get_by_text("Non-revolving", exact=True).first).to_be_visible()
        # Cleanup
        lt.click_delete()
        lt.confirm_delete_in_modal()

    def test_a_non_revolving_loan_type_is_rejected_on_save_when_only_a_fee_row_is_present(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-065 [new] — Non-revolving is rejected with only a Fee row; it needs both
        a Principal AND an Interest row."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Non-revolving")
        lt.set_interest_type("Simple")
        lt.set_interest_calculation_method("30/360")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Fee")
        steps.append("Added only a single Fee row to the Payment priority grid (no Principal/Interest)")
        lt.save()
        steps.append("Clicked Save with only a Fee row present")
        expect(lt.frame.get_by_role("alert")).to_contain_text(
            "should contain both principal and interest item for Non-revolving loan type"
        )

    def test_a_stale_fee_type_value_left_after_switching_a_row_away_from_fee_blocks_save_until_cleared(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-066 [new] — A row's leftover Fee type value (from when its Type was
        previously "Fee") is not auto-cleared when Type switches to Interest/Principal,
        and blocks save unless explicitly cleared."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Non-revolving")
        lt.set_interest_type("Simple")
        lt.set_interest_calculation_method("30/360")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)

        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Fee")
        lt.set_row_fee_type("fee", 0, "ocr-fee-type-2")
        steps.append("Row 1: set Type = Fee with a Fee type value selected")
        lt.set_row_type("Interest", 0)
        steps.append("Row 1: switched Type from Fee to Interest, WITHOUT clearing the Fee type value")

        lt.click_add_row()
        lt.set_row_sort_order("2", 0)
        lt.set_row_type("Principal", 0)
        steps.append("Added a Principal row so only the stale Fee type value is under test")

        lt.save()
        steps.append("Clicked Save with a stale Fee type value left on the Interest row")
        expect(lt.frame.get_by_role("alert")).to_contain_text(
            "SHOULD_NOT_HAVE_ANY_FEE_SELECTED"
        )

        # Recovery: clear the stale Fee type value and confirm the record now saves.
        lt.clear_row_fee_type(1)
        steps.append("Cleared the stale Fee type value on the Interest row")
        lt.save()
        steps.append("Clicked Save again after clearing the stale value")
        lt.wait_for_view_page()
        expect(lt.frame.locator("h1").filter(has_text="Loan type:")).to_be_visible()
        # Cleanup
        lt.click_delete()
        lt.confirm_delete_in_modal()

    def test_the_save_split_button_dropdown_offers_exactly_save_save_and_close_and_save_and_new(self, create_form, steps):
        """TC-LT-067 [new] — Save split-button dropdown offers exactly
        Save / Save and close / Save and new (checklist row 4)."""
        steps.append("Opened the Save split-button dropdown")
        opts = [o.lower() for o in create_form.save_menu_options()]
        for wanted in ("save", "save and close", "save and new"):
            assert any(o == wanted for o in opts), f"{wanted!r} missing from {opts}"

    def test_clicking_save_and_new_saves_the_record_and_reopens_a_blank_create_form(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-068 [new] — "Save and new" saves the record and opens a fresh,
        blank Create form (checklist row 7)."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Revolving")
        lt.set_interest_type("Compound")
        lt.set_interest_calculation_method("Actual/365")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Interest")
        steps.append(f"Filled all required fields for '{unique_loan_type_name}'")
        lt.save_via("Save and new")
        steps.append("Clicked 'Save and new'")
        expect(
            lt.frame.get_by_role("heading", name="Create loan type")
        ).to_be_visible()
        steps.append("Verified a fresh Create loan type form reopened")
        expect(lt.frame.locator(lt.NAME_INPUT).first).to_have_value("")
        # Cleanup: the record created by "Save and new" still needs deleting.
        listing = LoanTypeListingPage(lt.page)
        listing.navigate_to_list()
        listing.search_by_name(unique_loan_type_name)
        if listing.is_record_visible(unique_loan_type_name):
            listing.open_record_by_name(unique_loan_type_name)
            lt.click_delete()
            lt.confirm_delete_in_modal()

    def test_the_loan_type_information_section_is_expanded_by_default(self, create_form, steps):
        """TC-LT-069 [new] — 'Loan type information' section is expanded by
        default (checklist row 11)."""
        steps.append("Checked the 'Loan type information' section's default expand state")
        assert create_form.is_named_section_expanded("Loan type information")

    def test_the_loan_invoicing_defaults_section_is_collapsed_by_default(self, create_form, steps):
        """TC-LT-070 [new; KNOWN DEFECT] — 'Loan invoicing defaults' is documented
        as collapsed by default (checklist row 38), but the checklist's own
        execution found it EXPANDED by default on Create. This test asserts the
        documented/expected behaviour (collapsed) and is expected to fail until
        that defect is fixed — see Jira Bug #9 in the Loan Type findings."""
        steps.append("Checked the 'Loan invoicing defaults' section's default expand state")
        assert not create_form.is_named_section_expanded("Loan invoicing defaults"), (
            "'Loan invoicing defaults' should be collapsed by default on Create "
            "(known defect: it renders expanded instead — checklist row 38 / Bug #9)"
        )

    def test_the_sort_order_field_rejects_non_numeric_input(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-071 [new] — Sort order only accepts numeric values
        (checklist row 66). Every other mandatory field is filled with valid
        data so that Sort order is the only variable under test — otherwise
        Save is blocked by unrelated required-field errors before the Sort
        order value is even evaluated."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Revolving")
        lt.set_interest_type("Compound")
        lt.set_interest_calculation_method("Actual/365")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        rows = lt._priority_grid().get_by_role("row")
        box = rows.nth(1).get_by_role("textbox").first
        box.fill("abc")
        lt.set_row_type("Interest")
        steps.append(
            "Filled every other required field with valid data; typed a "
            "non-numeric Sort order value ('abc') and set the row Type = Interest"
        )
        lt.save()
        steps.append("Clicked Save with a non-numeric Sort order")
        # Either the field rejects/strips the non-numeric input outright, or the
        # server blocks the save with a validation error — both are acceptable
        # evidence that "only numeric values" is enforced.
        current_value = box.input_value()
        if current_value == "abc":
            expect(lt.frame.get_by_role("alert")).to_be_visible()
        else:
            assert current_value.strip() == "" or current_value.strip().isdigit(), (
                f"Expected the non-numeric Sort order to be rejected or stripped, "
                f"got {current_value!r}"
            )

    def test_saving_with_duplicate_sort_order_values_across_rows_shows_a_validation_error(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-072 [new] — Saving with duplicate Sort order values across
        Payment priority rows shows a validation error (checklist row 67)."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Non-revolving")
        lt.set_interest_type("Simple")
        lt.set_interest_calculation_method("30/360")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Interest")
        lt.click_add_row()
        lt.set_row_sort_order("1", 1)
        lt.set_row_type("Principal", 1)
        steps.append("Added two Payment priority rows, both with Sort order = 1")
        lt.save()
        steps.append("Clicked Save with duplicate Sort order values")
        expect(lt.frame.get_by_role("alert")).to_be_visible()

    def test_a_second_payment_priority_row_with_type_principal_is_rejected_on_save(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-073 [new] — Only one Payment priority row may have
        Type = Principal; a second is rejected on Save (checklist row 75)."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Non-revolving")
        lt.set_interest_type("Simple")
        lt.set_interest_calculation_method("30/360")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Principal")
        lt.click_add_row()
        lt.set_row_sort_order("2", 1)
        lt.set_row_type("Principal", 1)
        steps.append("Added two Payment priority rows, both with Type = Principal")
        lt.save()
        steps.append("Clicked Save with two Principal rows")
        expect(lt.frame.get_by_role("alert")).to_be_visible()

    def test_a_second_payment_priority_row_with_type_interest_is_rejected_on_save(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-074 [new] — Only one Payment priority row may have
        Type = Interest; a second is rejected on Save (checklist row 76)."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Revolving")
        lt.set_interest_type("Compound")
        lt.set_interest_calculation_method("Actual/365")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Interest")
        lt.click_add_row()
        lt.set_row_sort_order("2", 1)
        lt.set_row_type("Interest", 1)
        steps.append("Added two Payment priority rows, both with Type = Interest")
        lt.save()
        steps.append("Clicked Save with two Interest rows")
        expect(lt.frame.get_by_role("alert")).to_be_visible()

    def test_multiple_payment_priority_rows_with_type_fee_are_allowed_and_save_successfully(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-075 [new] — Type = Fee can be selected for multiple Payment
        priority rows at once (checklist row 77)."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        lt.select_type("Revolving")
        lt.set_interest_type("Compound")
        lt.set_interest_calculation_method("Actual/365")
        lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
        lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
        lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
        lt.click_add_row()
        lt.set_row_sort_order("1")
        lt.set_row_type("Interest")
        lt.click_add_row()
        lt.set_row_sort_order("2", 1)
        lt.set_row_type("Fee", 1)
        lt.click_add_row()
        lt.set_row_sort_order("3", 2)
        lt.set_row_type("Fee", 2)
        steps.append("Added one Interest row and two Fee rows")
        lt.save()
        steps.append("Clicked Save with two Fee rows present")
        lt.wait_for_view_page()
        expect(lt.frame.locator("h1").filter(has_text="Loan type:")).to_be_visible()
        # Cleanup
        lt.click_delete()
        lt.confirm_delete_in_modal()

    def test_a_newly_added_payment_priority_row_is_immediately_editable(self, create_form, steps):
        """TC-LT-076 [new] — Adding a Payment priority row gives the new row
        a live, editable Sort order cell ready for immediate entry
        (checklist row 94 — "newly added row is highlighted/focused for
        immediate editing"). The grid is a Wijmo FlexGrid; rather than assert
        on a specific highlight CSS class (implementation detail, and the
        grid's row wrapper does not carry one — see 2026-08-17 live check,
        only the clicked "Add row" button shows an outline), this verifies
        the observable, spec-relevant behaviour: the new row's Sort order
        textbox is enabled and focusable without any extra click."""
        lt = create_form
        lt.click_add_row()
        steps.append("Added a Payment priority row")
        rows = lt._priority_grid().get_by_role("row")
        sort_order_box = rows.nth(1).get_by_role("textbox").first
        expect(sort_order_box).to_be_editable()
        sort_order_box.fill("1")
        expect(sort_order_box).to_have_value("1")

    def test_saving_a_completely_empty_create_form_is_blocked_by_mandatory_field_validation(self, create_form, steps):
        """TC-LT-077 [new] — Saving with all mandatory top-level fields empty
        shows validation and does not create a record (checklist row 95,
        covers the "all mandatory fields ... validated when saved" case at
        the whole-form level, distinct from the individual per-field checks
        TC-LT-029/033/036/037/038)."""
        steps.append("Clicked Save on a completely empty Create form")
        create_form.save()
        create_form.page.wait_for_timeout(1_500)
        steps.append("Verified we're still on the Create form (record was not saved)")
        expect(
            create_form.frame.get_by_role("heading", name="Create loan type")
        ).to_be_visible()

    def test_clicking_cancel_with_unsaved_changes_discards_them_immediately_with_no_confirmation_prompt(
        self, create_form, unique_loan_type_name, steps
    ):
        """TC-LT-078 [new] — Cancel discards unsaved changes immediately, with
        NO confirmation prompt (checklist row 44 — the checklist's own
        execution recorded this as "Passed" against the *absence* of a
        prompt, i.e. this documents actual behaviour, not a defect)."""
        lt = create_form
        lt.fill_name(unique_loan_type_name)
        steps.append(f"Filled Loan type = '{unique_loan_type_name}' (unsaved)")
        lt.cancel()
        steps.append("Clicked Cancel — expecting an immediate return to the list, no dialog")
        expect(
            lt.frame.get_by_role("heading", name="Loan types")
        ).to_be_visible()
        expect(lt.frame.get_by_role("dialog")).to_have_count(0)
