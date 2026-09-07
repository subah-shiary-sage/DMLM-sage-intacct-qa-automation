"""
type_page.py
Page Object for the Loan Type Create / View / Edit / Delete pages
(Lending Management → Setup → Loan type).

Selectors verified against live DOM 2026-07-15 (DMLM entity).

Key behaviours discovered live:
  * Create page  : Save is role="menuitem"; Cancel is a visible button.
                   Fields: Loan type (name, required), Description (optional),
                   Type (required radio: Revolving/Non-revolving), Interest type
                   (required combobox: Simple/Compound), Interest calculation
                   method (required combobox — CONDITIONALLY rendered only after
                   Type is selected), Order Entry transaction definition /
                   Item for loan principal posting / Item for loan interest
                   posting (all required pickers). NO Status field on Create.
                   Payment priority order grid: at least one row is REQUIRED to
                   save, and each row's Sort order is REQUIRED (both are
                   server-side validations, not documented anywhere in the UI).
                   Non-revolving specifically requires BOTH a Principal row
                   AND an Interest row (a single row of either type is
                   rejected) — see TEST_CASES_Loan_Type.md TC-LT-065.
  * View page    : H1 is "Loan type: <ID>" — no name in the heading (differs
                   from Depository Account Category's "<ID>--<Name>" pattern).
                   Edit / Delete are directly visible in the header (not nested);
                   a separate three-dot "More actions" holds "View audit trail".
                   Status IS shown here (defaults to Active).
  * Edit page    : H1 is "Edit loan-management/loan-type: <ID>--<Name>". Type
                   renders as read-only plain text (cannot be changed). Status
                   is an editable combobox. Save/Cancel are collapsed into the
                   header "More actions" overflow.
  * Delete modal : dialog "Delete loan type" with Delete / Cancel. Same
                   framework component as Depository Account Category's delete
                   modal — the [role="dialog"] wrapper itself is an unreliable
                   Playwright-visibility target (zero-bbox quirk), so assertions
                   and waits target the heading / buttons instead.
"""

from typing import Optional
from ..base_page import BasePage


class LoanTypePage(BasePage):

    # ── Field selectors ────────────────────────────────────────────────────────
    NAME_INPUT        = 'input[aria-label="Loan type"]'
    DESCRIPTION_INPUT = 'input[aria-label="Description"]'

    # ── Collapsible section ────────────────────────────────────────────────────
    SECTION_HEADER = "Loan type information"

    # ── Delete confirmation modal ──────────────────────────────────────────────
    DELETE_DIALOG = "Delete loan type"

    # ── Validation errors (inline + toast) ─────────────────────────────────────
    VALIDATION_ERROR = '[aria-invalid="true"], [class*="error"], [role="alert"]'

    # ══════════════════════════════════════════════════════════════════════════
    # Page heading helpers
    # ══════════════════════════════════════════════════════════════════════════

    def get_page_title(self) -> str:
        return self.frame.locator("h1").first.inner_text()

    def wait_for_view_page(self, timeout: int = 15_000):
        """Wait for the read-only View page heading 'Loan type: <ID>'."""
        self.frame.locator("h1").filter(
            has_text="Loan type:"
        ).filter(has_not_text="Edit").filter(has_not_text="Create").first.wait_for(timeout=timeout)

    def wait_for_edit_page(self, timeout: int = 10_000):
        self.frame.locator("h1").filter(has_text="Edit").filter(
            has_text="loan-type"
        ).first.wait_for(timeout=timeout)

    # ══════════════════════════════════════════════════════════════════════════
    # Form interactions (Create & Edit)
    # ══════════════════════════════════════════════════════════════════════════

    def fill_name(self, name: str):
        inp = self.frame.locator(self.NAME_INPUT).first
        inp.fill(name)
        inp.evaluate("el => el.blur()")

    def get_name_value(self) -> str:
        return self.frame.locator(self.NAME_INPUT).first.input_value()

    def fill_description(self, description: str):
        self.frame.locator(self.DESCRIPTION_INPUT).first.fill(description)

    def select_type(self, type_label: str):
        """Type radio button — 'Revolving' or 'Non-revolving'. Create page only
        (read-only on Edit)."""
        self.frame.get_by_role("radio", name=type_label, exact=True).click()

    def get_selected_type_text(self) -> str:
        """Read-only Type value on the Edit/View page (plain text, not a radio)."""
        return self.frame.get_by_text("Type", exact=True).locator(
            "xpath=following-sibling::*[1]"
        ).inner_text()

    def _select_combobox_option(self, combobox_name: str, option_label: str, retries: int = 2):
        """
        Select an option from a combobox, retrying the whole open→click cycle
        in case the option list doesn't appear on the first attempt.

        NOTE (2026-08-17): live testing found the "Interest calculation
        method" combobox failing to open its option list AT ALL on this
        date — 0 elements anywhere on the page carry role="option" after
        clicking it and waiting 1.5s, reproduced both headless and headed,
        and on the pre-existing (unmodified) TC-LT-034 test too. This is an
        outage in the live app itself, not a timing race this retry can
        paper over — if it recurs, check the app/environment before
        assuming a test or selector problem. The retry loop is kept because
        it is a correct, low-cost defense against genuine transient
        raciness in conditionally-rendered fields, which is a real and
        separate failure mode from the total outage observed on this date.
        """
        combo = self.frame.get_by_role("combobox", name=combobox_name).first
        combo.wait_for(state="visible", timeout=10_000)
        last_error = None
        for attempt in range(retries + 1):
            combo.click()
            option = self.frame.get_by_role("option", name=option_label, exact=True)
            try:
                option.first.wait_for(state="visible", timeout=5_000)
                option.first.click()
                return
            except Exception as exc:
                last_error = exc
                self.page.wait_for_timeout(500)
        try:
            self.frame.get_by_text(option_label, exact=True).first.click()
        except Exception:
            raise last_error

    def set_interest_type(self, value: str):
        """'Simple' or 'Compound'."""
        self._select_combobox_option("Interest type", value)

    def set_interest_calculation_method(self, value: str):
        """Only present after Type has been selected (conditionally rendered)."""
        self._select_combobox_option("Interest calculation method", value)

    def set_status(self, status: str):
        """Status combobox — Edit page only ('Active' / 'Inactive')."""
        self._select_combobox_option("Status", status)

    def set_order_entry_transaction_definition(self, query: str, option_text: Optional[str] = None):
        self.fill_picker("Order Entry transaction definition", query, option_text)

    def set_item_for_principal_posting(self, query: str, option_text: Optional[str] = None):
        self.fill_picker("Item for loan principal posting", query, option_text)

    def set_item_for_interest_posting(self, query: str, option_text: Optional[str] = None):
        self.fill_picker("Item for loan interest posting", query, option_text)

    # ══════════════════════════════════════════════════════════════════════════
    # Payment priority order grid
    # ══════════════════════════════════════════════════════════════════════════

    def _priority_grid(self):
        return self.frame.get_by_role("grid").first

    def get_payment_priority_row_count(self) -> int:
        return self._priority_grid().locator("tbody tr, [role='row']").count() - 1  # minus header

    def click_add_row(self):
        self.frame.get_by_role("button", name="Add row").first.click()
        self.page.wait_for_timeout(400)

    def click_remove_row(self, row_index: int = 0):
        rows = self._priority_grid().get_by_role("row")
        rows.nth(row_index + 1).get_by_role("button", name="Remove row").click()
        self.page.wait_for_timeout(400)

    def set_row_sort_order(self, value: str, row_index: int = 0):
        rows = self._priority_grid().get_by_role("row")
        rows.nth(row_index + 1).get_by_role("textbox").first.fill(value)

    def set_row_type(self, value: str, row_index: int = 0):
        rows = self._priority_grid().get_by_role("row")
        combo = rows.nth(row_index + 1).get_by_role("combobox").first
        combo.click()
        option = self.frame.get_by_role("option", name=value, exact=True)
        option.first.wait_for(state="visible", timeout=5_000)
        option.first.click()

    def is_row_fee_type_enabled(self, row_index: int = 0) -> bool:
        rows = self._priority_grid().get_by_role("row")
        fee_combo = rows.nth(row_index + 1).get_by_role("combobox").nth(1)
        return fee_combo.is_enabled()

    def _activate_row(self, row_index: int = 0):
        """
        Click into a row's Fee type cell to make it editable — a row that
        isn't the grid's currently "active"/selected row renders its cells as
        plain text rather than live inputs.
        """
        rows = self._priority_grid().get_by_role("row")
        rows.nth(row_index + 1).get_by_role("gridcell").nth(2).click()

    def set_row_fee_type(self, query: str, row_index: int = 0, option_text: Optional[str] = None):
        """Only meaningful when the row's Type = Fee (see is_row_fee_type_enabled)."""
        self._activate_row(row_index)
        rows = self._priority_grid().get_by_role("row")
        combo = rows.nth(row_index + 1).get_by_role("combobox").nth(1)
        combo.click()
        combo.fill(query)
        target = option_text or query
        option = self.frame.get_by_role("option", name=target, exact=False)
        option.first.wait_for(state="visible", timeout=8_000)
        option.first.click()

    def clear_row_fee_type(self, row_index: int = 0):
        """
        Clear a stale Fee type value left over from a row that was
        previously Type = Fee. Switching a row's Type away from "Fee" does
        NOT auto-clear its Fee type value (a framework quirk — see
        TEST_CASES_Loan_Type.md TC-LT-066); a leftover value blocks save with
        "PRINCIPAL_OR_INTEREST_SHOULD_NOT_HAVE_ANY_FEE_SELECTED".
        """
        self._activate_row(row_index)
        rows = self._priority_grid().get_by_role("row")
        combo = rows.nth(row_index + 1).get_by_role("combobox").nth(1)
        combo.click()
        self.page.keyboard.press("ControlOrMeta+a")
        self.page.keyboard.press("Delete")

    # ══════════════════════════════════════════════════════════════════════════
    # Save / Cancel  (robust across Create menuitem vs Edit overflow)
    # ══════════════════════════════════════════════════════════════════════════

    def save(self):
        self.click_header_action("Save")

    def cancel(self):
        self.click_header_action("Cancel")

    def save_menu_options(self) -> list[str]:
        """
        Labels in the Save split-button dropdown.

        Save is a split control: the caret next to it opens Save / Save and
        close / Save and new (Edit page: Save / Save and close only). At
        narrow widths the whole thing collapses into the header overflow, so
        fall back to that.
        """
        caret = self.frame.locator(
            '[aria-label="Save"] ~ button, [aria-label="More actions"]:visible'
        )
        if caret.count():
            caret.first.click()
            self.page.wait_for_timeout(600)
        items = self.frame.locator('[role="menuitem"], [role="dialog"] button')
        return [
            t
            for t in ((items.nth(i).inner_text() or "").strip() for i in range(items.count()))
            if t
        ]

    def save_via(self, option: str):
        """Save using a named variant: 'Save', 'Save and close', 'Save and new'."""
        if option == "Save":
            self.save()
            return
        self.click_header_action("Save")
        self.page.wait_for_timeout(400)
        target = self.frame.get_by_role("button", name=option).or_(
            self.frame.locator(f'[role="menuitem"]:has-text("{option}")')
        )
        target.first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # View page actions
    # ══════════════════════════════════════════════════════════════════════════

    def click_edit(self):
        self.click_header_action("Edit")
        self.wait_for_edit_page()

    def click_delete(self):
        self.click_header_action("Delete")
        # Wait on the heading, not the dialog role element — the dialog's own
        # [role="dialog"] wrapper has a zero-size bounding box (framework
        # quirk shared with Depository Account Category's delete modal; see
        # DepositoryAccountCategoryPage._delete_dialog for the full writeup).
        # `.last` because the session-scoped page can accumulate stale,
        # unmounted confirm-dialog instances from earlier tests.
        self.frame.get_by_role("heading", name=self.DELETE_DIALOG).last.wait_for(timeout=10_000)

    def click_back_to_list(self):
        link = self.frame.get_by_role("link", name="Loan types")
        if link.count() > 0 and link.first.is_visible():
            link.first.click()
        else:
            self.frame.get_by_role(
                "button", name="Back to previous page"
            ).first.click()
        self.frame.get_by_role(
            "heading", name="Loan types"
        ).wait_for(timeout=10_000)

    def is_name_readonly(self) -> bool:
        return self.frame.locator(self.NAME_INPUT).count() == 0

    def get_field_text(self, field_label: str) -> str:
        return self.frame.get_by_label(field_label).first.inner_text()

    # ══════════════════════════════════════════════════════════════════════════
    # Three-dot menu (View page) — nested inside header "More actions"
    # ══════════════════════════════════════════════════════════════════════════

    def open_view_three_dot_menu(self):
        self._open_header_more_actions()
        self.frame.locator('[aria-label="More actions"]:visible').last.click()
        self.page.wait_for_timeout(400)

    def get_three_dot_menu_items(self) -> list[str]:
        self.open_view_three_dot_menu()
        dialogs = self.frame.get_by_role("dialog")
        items = dialogs.last.get_by_role("button").all()
        return [i.inner_text().strip() for i in items if i.inner_text().strip()]

    def click_view_audit_trail(self):
        self.open_view_three_dot_menu()
        self.frame.get_by_role("button", name="View audit trail").first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # Collapsible section
    # ══════════════════════════════════════════════════════════════════════════

    def _get_section_toggle(self):
        return self.frame.locator(
            'button[aria-label="IA.COLLAPSE"], button[aria-label="IA.EXPAND"]'
        ).first

    def is_section_expanded(self) -> bool:
        label = self._get_section_toggle().get_attribute("aria-label") or ""
        return "COLLAPSE" in label.upper()

    def minimize_section(self):
        if self.is_section_expanded():
            self._get_section_toggle().click()
            self.page.wait_for_timeout(400)

    def maximize_section(self):
        if not self.is_section_expanded():
            self._get_section_toggle().click()
            self.page.wait_for_timeout(400)

    def _get_named_section_toggle(self, section_label: str):
        """
        Locate the collapse/expand chevron for a specific section by its
        heading text (unlike _get_section_toggle(), which always targets the
        first section on the page). Needed to check e.g. "Loan invoicing
        defaults" independently of "Loan type information".
        """
        heading = self.frame.get_by_text(section_label, exact=True).first
        return heading.locator(
            "xpath=ancestor::*[self::div or self::section][1]"
            '//button[@aria-label="IA.COLLAPSE" or @aria-label="IA.EXPAND"]'
        ).first

    def is_named_section_expanded(self, section_label: str) -> bool:
        label = self._get_named_section_toggle(section_label).get_attribute("aria-label") or ""
        return "COLLAPSE" in label.upper()

    # ══════════════════════════════════════════════════════════════════════════
    # Delete confirmation modal
    # ══════════════════════════════════════════════════════════════════════════

    def confirm_delete_in_modal(self):
        self.confirm_delete()

    def cancel_delete_in_modal(self):
        self.cancel_delete()

    # ══════════════════════════════════════════════════════════════════════════
    # Validation helpers
    # ══════════════════════════════════════════════════════════════════════════

    def get_first_validation_error(self):
        return self.frame.locator(self.VALIDATION_ERROR).first

    def get_error_banner_text(self) -> str:
        return self.frame.get_by_role("alert").first.inner_text()

    # ══════════════════════════════════════════════════════════════════════════
    # Field metadata (presence / mandatory markers) — used to compare the
    # Create page's mandatory-field set against the Edit page's, per
    # TEST_CASES_Loan_Type.md multi-entity item E1 / F11 (mandatory-marker
    # parity).
    # ══════════════════════════════════════════════════════════════════════════

    def is_field_mandatory(self, label: str) -> bool:
        """True when the field's label carries the red mandatory asterisk."""
        return self.page.evaluate(
            """(label) => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const norm = s => s.replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
                return [...d.querySelectorAll('label')]
                    .some(e => norm(e.textContent).replace(/\\s*\\*$/, '') === label
                            && norm(e.textContent).endsWith('*'));
            }""",
            label,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Payment priority order grid — row-level Type column inspection, used to
    # verify Principal/Interest are single-row-only while Fee can repeat.
    # ══════════════════════════════════════════════════════════════════════════

    def get_row_type_value(self, row_index: int) -> str:
        rows = self._priority_grid().get_by_role("row")
        combo = rows.nth(row_index + 1).get_by_role("combobox").first
        text = (combo.inner_text() or "").strip()
        if text:
            return text
        try:
            return (combo.input_value() or "").strip()
        except Exception:
            return ""

    def get_all_row_type_values(self) -> list[str]:
        count = self.get_payment_priority_row_count()
        return [self.get_row_type_value(i) for i in range(count)]
