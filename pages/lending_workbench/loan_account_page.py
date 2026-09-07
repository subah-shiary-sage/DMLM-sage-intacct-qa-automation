"""
loan_account_page.py
Page Objects for Loan accounts (Lending Management → Loan accounts):
  - LoanAccountListingPage : the list  (config snl.loan-account.list)
  - LoanAccountPage        : create / view (config snl.loan-account.create)

Field set derived from the SNLLOANACCOUNT schema (p309):
  ACCOUNTID, NAME, LOANCATEGORYKEY, CUSTOMERKEY/VENDORKEY, LOANTYPEKEY,
  INTERESTRATEKEY, TERMINMONTH, ORIGINATIONDATE, FIRSTPAYMENTDATE,
  ORIGINATIONAMOUNT, ...

⚠ The exact create-form selectors (aria-labels / picker option formats) were
NOT captured live (the p309 session timed out during exploration). They follow
the standard Intacct xgPage patterns used by the Loan Type / Loan Interest Rate
page objects and are expected to need minor verification on the first live run
— the same "build then fix on run" flow used for the other modules.
"""

from typing import Optional
from ..base_page import BasePage


class LoanAccountListingPage(BasePage):

    LIST_HEADING = "Loan accounts"
    CREATE_BTN = '[aria-label="Create"]'

    def navigate_to_list(self):
        page = self.page
        already_active = page.evaluate(
            """() => {
                const byText = (t) => Array.from(document.querySelectorAll('a'))
                    .find(a => a.textContent.trim() === t
                            && (a.getAttribute('href') || '').startsWith('javascript:void'));
                const lending = byText('Lending Management');
                if (lending) { lending.click(); return true; }
                const depo = byText('Depository Management');
                if (depo) { depo.click(); return false; }
                return false;
            }"""
        )
        page.wait_for_timeout(800)
        if not already_active:
            page.evaluate(
                """() => {
                    const link = Array.from(document.querySelectorAll('a'))
                        .find(a => a.textContent.trim() === 'Lending Management'
                                && (a.getAttribute('href') || '').startsWith('javascript:void'));
                    if (link) link.click();
                }"""
            )
            page.wait_for_timeout(800)
        page.evaluate(
            """() => {
                const link = document.querySelector('a[href*="loan-account.list"]');
                if (link) link.click();
            }"""
        )
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=20_000)
        self.frame.locator(self.CREATE_BTN).first.wait_for(state="visible", timeout=10_000)

    def click_create(self):
        self.frame.locator(self.CREATE_BTN).first.click()
        self.frame.get_by_role("heading", name="Create loan account").wait_for(timeout=15_000)

    def _name_filter(self):
        return self.frame.locator('input[aria-label="Loan"][placeholder="Contains"], '
                                  'input[aria-label="Name"][placeholder="Contains"]').first

    def search_by_id(self, account_id: str):
        box = self._name_filter()
        box.fill(account_id)
        self.page.wait_for_timeout(300)
        box.press("Enter")
        self.page.wait_for_timeout(1_500)

    def is_record_visible(self, account_id: str) -> bool:
        return self.frame.get_by_role("link", name=account_id, exact=True).count() > 0

    def open_record(self, account_id: str):
        self.frame.get_by_role("link", name=account_id, exact=True).first.click()
        self.page.wait_for_timeout(1_000)


class LoanAccountPage(BasePage):

    ACCOUNT_ID_INPUT = 'input[aria-label="Account ID"], input[aria-label="Loan account ID"]'
    NAME_INPUT = 'input[aria-label="Name"]'

    # ── Field helpers ───────────────────────────────────────────────────────────
    def fill_account_id(self, value: str):
        self.frame.locator(self.ACCOUNT_ID_INPUT).first.fill(value)

    def fill_name(self, value: str):
        self.frame.locator(self.NAME_INPUT).first.fill(value)

    def _fill_picker(self, field_label: str, query: str, option_label: Optional[str] = None):
        """Type into a picker/combobox and choose the matching option."""
        combo = self.frame.get_by_role("combobox", name=field_label).first
        combo.click()
        combo.fill(query)
        option = self.frame.get_by_role("option", name=(option_label or query))
        try:
            option.first.wait_for(state="visible", timeout=8_000)
            option.first.click()
        except Exception:
            self.frame.get_by_text(option_label or query, exact=False).first.click()

    def set_loan_category(self, category: str):
        self._fill_picker("Loan category", category)

    def set_customer(self, customer: str):
        self._fill_picker("Customer", customer)

    def set_loan_type(self, loan_type: str):
        self._fill_picker("Loan type", loan_type)

    def set_interest_rate(self, rate_name: str):
        self._fill_picker("Interest rate", rate_name)

    def set_origination_amount(self, amount: str):
        self.frame.get_by_role("textbox", name="Origination amount").first.fill(amount)

    def set_origination_date(self, value: str):
        """value MM/DD/YYYY."""
        box = self.frame.get_by_role("combobox", name="Origination date").first
        box.click()
        box.fill(value)
        self.page.keyboard.press("Tab")

    def set_first_payment_date(self, value: str):
        box = self.frame.get_by_role("combobox", name="First payment date").first
        box.click()
        box.fill(value)
        self.page.keyboard.press("Tab")

    def set_term_in_months(self, months: str):
        self.frame.get_by_role("textbox", name="Term").first.fill(months)

    # ── Save / actions (Create page: Save is a header menuitem) ─────────────────
    def _click_action(self, name: str, direct_timeout: int = 2_000):
        direct = self.frame.locator(
            f'[aria-label="{name}"]:visible, '
            f'[role="menuitem"]:has-text("{name}"):visible, '
            f'button:has-text("{name}"):visible'
        )
        try:
            direct.first.wait_for(state="visible", timeout=direct_timeout)
            direct.first.click()
            return
        except Exception:
            pass
        self.frame.locator('[aria-label="More actions"]:visible').first.click()
        self.page.wait_for_timeout(400)
        self.frame.locator(
            f'[aria-label="{name}"]:visible, [role="menuitem"]:has-text("{name}"):visible, '
            f'button:has-text("{name}"):visible'
        ).first.click()

    def save(self):
        self._click_action("Save")

    def cancel(self):
        self._click_action("Cancel")

    def wait_for_view_page(self, timeout: int = 20_000):
        self.frame.locator("h1").filter(has_text="Loan account").filter(
            has_not_text="Create").filter(has_not_text="Edit").first.wait_for(timeout=timeout)

    def get_error_banner_text(self) -> str:
        return self.frame.get_by_role("alert").first.inner_text()
