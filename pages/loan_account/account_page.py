"""
account_page.py
Page Object for the Loan account Create / View / Edit / Delete pages
(Lending Management → All → Loan account).

Selectors verified against live DOM 2026-08-17 (release www-p303, LME entity).

Key behaviours discovered live:
  * Create page  : H1 "Create loan". Four sections: "Loan information",
                   "Loan terms", "Dimensions", "Disbursement".
                   Loan information fields: Account category* (picker),
                   Account number* (text — becomes read-only/auto-generated
                   when the chosen category has a document sequence),
                   Amount* (numeric), Account name* (text), Customer*
                   (picker), Vendor* (picker), Email statements (checkbox,
                   unchecked by default), Attachment (optional picker),
                   Description (optional, 500-char limit despite the
                   checklist saying 1000).
                   Loan terms fields are CONDITIONALLY rendered: only
                   Loan type* (picker) and Loan origination date* show up
                   front. After Loan type is selected, Interest rate*,
                   Term in months* and First payment date* appear (for a
                   Non-revolving type). A Revolving type instead reveals a
                   "Create amortization schedule" checkbox and (if checked)
                   the same Term/First-payment fields, plus an optional
                   Renewal date.
                   Dimensions: Department, Location, Project, Employee, Item,
                   Class, Contract — all optional pickers.
                   Disbursement: Disbursement recipient, Bill number.
  * View page    : H1 "Loan: <ID>" (record ID, NOT the account number).
                   Tabs: Overview (+ Amortization schedule, if a schedule was
                   created) + Transaction history. Edit/Delete are directly
                   visible in the header, plus a three-dot "More actions"
                   with "View audit trail" and "Object definition".
                   Account category / Customer / Vendor / Interest rate /
                   Loan type are drillable links; Location and State are
                   plain text (checklist flags this as a defect — Location
                   is documented as drillable but isn't).
  * Edit page    : H1 exposes the internal object path — known defect, same
                   pattern as Loan Type: "Edit loan-management/loan-account:
                   <account number>--<account name>". Account category,
                   Account number, Customer and Vendor are all READ-ONLY on
                   Edit (Customer/Vendor lock immediately, not just after a
                   transaction — checklist flags this too). Term in months
                   and First payment date are ABSENT from the Edit page's
                   Loan terms section (present on Create/View) — another
                   documented defect.
  * Delete modal : dialog "Delete loan account" (note: NOT "Delete loan
                   Account" — checklist's casing expectation is wrong, the
                   app is consistently lowercase like every other LME
                   delete modal). Confirmation message IS properly
                   localised: "The following loan account will be
                   permanently deleted: <account name>" — verified live
                   2026-08-17. The checklist's claim of a raw i18n key here
                   appears to already be fixed (matches the Bug #13/#14/#19-
                   #21/#24 pattern of previously-open i18n leaks that were
                   since retested/closed).

Confirmed end-to-end 2026-08-17: Create (non-revolving "Compound_Amortized"
loan type, category with no document sequence so Account number is a plain
required text field) -> Save -> View ("Loan: <record id>", tabs Overview /
Amortization schedule / Transaction history) -> Edit (read-only Account
number/Customer/Vendor/Account category/Loan type/Loan origination date/
Interest rate; editable Amount/Account name/Description) -> Cancel -> Delete
modal -> Cancel. All fields save correctly including Location and First
payment date once using the fixes captured in fill_account_name() and
set_first_payment_date() below.

KNOWN DEFECT — Revolving loan type + "Create amortization schedule" checkbox:
saving crashes with raw client-side exceptions surfaced as user-facing error
toasts: "Cannot read properties of undefined (reading 'placeholders')",
"/ by zero", "InvocationTargetException" (x3). Confirmed reproducible twice
in a row on Loan type "2--Loan Type 01" (Revolving). The Create form is left
in a broken, un-savable state — Save does not error gracefully, it renders a
stack of raw runtime exceptions. This should be tested as an EXPECTED FAILURE
path (assert the error toasts appear / the record is NOT created), not
exercised as a working create route for other Revolving-type test scenarios.
"""

from typing import Optional
from ..base_page import BasePage


class LoanAccountPage(BasePage):

    # ── Field selectors ────────────────────────────────────────────────────────
    ACCOUNT_NAME_INPUT = 'input[aria-label="Account name"]'
    ACCOUNT_NUMBER_INPUT = 'input[aria-label="Account number"]'
    AMOUNT_INPUT = 'input[aria-label="Amount"]'
    DESCRIPTION_INPUT = 'input[aria-label="Description"], textarea[aria-label="Description"]'
    TERM_IN_MONTHS_INPUT = 'input[aria-label="Term in months"]'

    # ── Delete confirmation modal ──────────────────────────────────────────────
    DELETE_DIALOG = "Delete loan account"

    # ── Validation errors (inline + toast) ─────────────────────────────────────
    VALIDATION_ERROR = '[aria-invalid="true"], [class*="error"], [role="alert"]'

    # ══════════════════════════════════════════════════════════════════════════
    # Page heading helpers
    # ══════════════════════════════════════════════════════════════════════════

    def get_page_title(self) -> str:
        return self.frame.locator("h1").first.inner_text()

    def wait_for_view_page(self, timeout: int = 20_000):
        """Wait for the read-only View page heading 'Loan: <ID>'."""
        self.frame.locator("h1").filter(
            has_text="Loan:"
        ).filter(has_not_text="Edit").filter(has_not_text="Create").first.wait_for(timeout=timeout)

    def wait_for_edit_page(self, timeout: int = 10_000):
        self.frame.locator("h1").filter(has_text="Edit").filter(
            has_text="loan-account"
        ).first.wait_for(timeout=timeout)

    # ══════════════════════════════════════════════════════════════════════════
    # Form interactions (Create & Edit)
    # ══════════════════════════════════════════════════════════════════════════

    def fill_account_name(self, name: str):
        """
        Retries the fill if the value doesn't stick. When Account category
        has no document sequence, Account number becomes an editable field
        just above Account name; the re-render that follows can intermittently
        swallow a `.fill()` issued right after, leaving the input empty even
        though the DOM node itself never changes — verified live 2026-08-17.
        """
        inp = self.frame.locator(self.ACCOUNT_NAME_INPUT).first
        for _ in range(3):
            inp.fill(name)
            inp.evaluate("el => el.blur()")
            if inp.input_value() == name:
                return
            self.page.wait_for_timeout(400)
        inp.fill(name)
        inp.evaluate("el => el.blur()")

    def get_account_name_value(self) -> str:
        return self.frame.locator(self.ACCOUNT_NAME_INPUT).first.input_value()

    def fill_account_number(self, value: str):
        self.frame.locator(self.ACCOUNT_NUMBER_INPUT).first.fill(value)

    def get_account_number_value(self) -> str:
        return self.frame.locator(self.ACCOUNT_NUMBER_INPUT).first.input_value()

    def is_account_number_readonly(self) -> bool:
        """
        True when Account number cannot be edited — covers BOTH the
        Create-page case (a disabled/auto-generated <input>, still present
        in the DOM) and the Edit-page case (no <input> at all; the field
        renders as plain read-only text — verified live 2026-08-17). Without
        the explicit count() check, `.is_editable()` on a zero-match locator
        waits its full default timeout before raising, rather than
        returning a usable boolean.
        """
        box = self.frame.locator(self.ACCOUNT_NUMBER_INPUT).first
        if box.count() == 0:
            return True
        return not box.is_editable()

    def fill_amount(self, value: str):
        self.frame.locator(self.AMOUNT_INPUT).first.fill(value)

    def fill_description(self, text: str):
        self.frame.locator(self.DESCRIPTION_INPUT).first.fill(text)

    def fill_term_in_months(self, months: str):
        self.frame.locator(self.TERM_IN_MONTHS_INPUT).first.fill(months)

    def _select_picker_option(self, field_label: str, query: str, option_text: Optional[str] = None, index: int = 0):
        """
        Search-as-you-type combobox: click, type a query, wait for the
        server-populated option list, then click the option at `index`
        (default first) or the one matching `option_text` exactly.
        """
        combo = self.frame.get_by_role("combobox", name=field_label).first
        combo.click()
        combo.fill(query)
        if option_text:
            option = self.frame.get_by_role("option", name=option_text, exact=True)
            try:
                option.first.wait_for(state="visible", timeout=8_000)
                option.first.click()
                return
            except Exception:
                self.frame.get_by_text(option_text, exact=True).first.click()
                return
        options = self.frame.get_by_role("option")
        options.first.wait_for(state="visible", timeout=8_000)
        options.nth(index).click()

    def set_account_category(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("Account category", query, option_text)

    def set_customer(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("Customer", query, option_text)

    def set_vendor(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("Vendor", query, option_text)

    def set_loan_type(self, query: str, option_text: Optional[str] = None):
        """Conditionally reveals Interest rate / Term in months / First
        payment date (non-revolving) or the amortization checkbox
        (revolving) after selection — give the app a moment to re-render."""
        self._select_picker_option("Loan type", query, option_text)
        self.page.wait_for_timeout(1_000)

    def set_interest_rate(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("Interest rate", query, option_text)

    def set_location(self, query: str, option_text: Optional[str] = None):
        """
        NOTE: live DOM has the Dimensions section's aria-labels in
        lowercase ("location", "department", ...) unlike every other field
        on the form (which are sentence-case). Verified 2026-08-17.
        """
        self._select_picker_option("location", query, option_text)

    def set_department(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("department", query, option_text)

    def set_project(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("project", query, option_text)

    def set_employee(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("employee", query, option_text)

    def set_item(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("item", query, option_text)

    def set_class(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("class", query, option_text)

    def set_contract(self, query: str, option_text: Optional[str] = None):
        self._select_picker_option("contract", query, option_text)

    def set_first_payment_date(self, value: str):
        """
        value MM/DD/YYYY. Unlike Loan origination date, this input has NO
        explicit role="combobox" attribute (type="tel", no role), so
        Playwright's accessibility tree resolves it as role="textbox" —
        verified live 2026-08-17.
        """
        box = self.frame.get_by_role("textbox", name="First payment date").first
        box.click()
        box.fill(value)
        self.page.keyboard.press("Tab")

    def set_renewal_date(self, value: str):
        """value MM/DD/YYYY. Same textbox-role quirk as First payment date."""
        box = self.frame.get_by_role("textbox", name="Renewal date").first
        box.click()
        box.fill(value)
        self.page.keyboard.press("Tab")

    def set_origination_date(self, value: str):
        """
        value MM/DD/YYYY. This one DOES carry an explicit role="combobox"
        (verified live 2026-08-17) — the only date field on this form that
        does.
        """
        box = self.frame.get_by_role("combobox", name="Loan origination date").first
        box.click()
        box.fill(value)
        self.page.keyboard.press("Tab")

    def toggle_email_statements(self):
        self.frame.get_by_role("checkbox", name="Email statements").first.click()

    def is_email_statements_checked(self) -> bool:
        return self.frame.get_by_role("checkbox", name="Email statements").first.is_checked()

    def toggle_create_amortization_schedule(self):
        """Revolving-only checkbox that reveals Term in months / First
        payment date and enables the 'Preview amortization schedule' link."""
        self.frame.get_by_role(
            "checkbox", name="Create amortization schedule"
        ).first.click()

    def has_create_amortization_checkbox(self) -> bool:
        return self.frame.get_by_role(
            "checkbox", name="Create amortization schedule"
        ).count() > 0

    def click_preview_amortization_schedule(self):
        self.frame.get_by_text("Preview amortization schedule", exact=False).first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # Save / Cancel  (robust across Create menuitem vs Edit overflow)
    # ══════════════════════════════════════════════════════════════════════════

    def save(self):
        self.click_header_action("Save")

    def cancel(self):
        self.click_header_action("Cancel")

    def save_menu_options(self) -> list[str]:
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
        self.frame.get_by_role("heading", name=self.DELETE_DIALOG).last.wait_for(timeout=10_000)

    def click_back_to_list(self):
        link = self.frame.get_by_role("link", name="Loans")
        if link.count() > 0 and link.first.is_visible():
            link.first.click()
        else:
            self.frame.get_by_role(
                "button", name="Back to previous page"
            ).first.click()
        self.frame.get_by_role(
            "heading", name="Loans"
        ).wait_for(timeout=10_000)

    def get_field_text(self, field_label: str) -> str:
        return self.frame.get_by_label(field_label).first.inner_text()

    def get_tab_names(self) -> list[str]:
        tabs = self.frame.get_by_role("tab").all()
        return [t.inner_text().strip() for t in tabs]

    def click_tab(self, name: str):
        self.frame.get_by_role("tab", name=name).first.click()
        self.page.wait_for_timeout(800)

    # ══════════════════════════════════════════════════════════════════════════
    # Three-dot menu (View page) — nested inside header "More actions"
    # ══════════════════════════════════════════════════════════════════════════

    def open_view_three_dot_menu(self):
        self._open_header_more_actions()
        self.frame.locator('[aria-label="More actions"]:visible').last.click()
        self.page.wait_for_timeout(400)

    def click_view_audit_trail(self):
        self.open_view_three_dot_menu()
        self.frame.get_by_role("button", name="View audit trail").first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # Delete confirmation modal
    # ══════════════════════════════════════════════════════════════════════════

    def confirm_delete_in_modal(self):
        self.confirm_delete()

    def cancel_delete_in_modal(self):
        self.cancel_delete()

    # ══════════════════════════════════════════════════════════════════════════
    # Field metadata (presence / mandatory markers)
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

    def has_field(self, label: str) -> bool:
        labels = self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                return [...d.querySelectorAll('label')]
                    .map(e => e.textContent.replace(/\\u00a0/g,' ').trim().replace(/\\s*\\*$/, ''));
            }"""
        )
        return label in labels

    # ══════════════════════════════════════════════════════════════════════════
    # Validation helpers
    # ══════════════════════════════════════════════════════════════════════════

    def get_first_validation_error(self):
        return self.frame.locator(self.VALIDATION_ERROR).first

    def get_error_banner_text(self) -> str:
        return self.frame.get_by_role("alert").first.inner_text()
