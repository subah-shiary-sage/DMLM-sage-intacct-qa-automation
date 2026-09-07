"""
workbench_page.py
Page Object for the Lending Workbench lister
(Lending Management → Lending workbench).

Verified against live DOM 2026-07-21 (p309, company snltahmid1b / CNY#
30901031134347, entity "United States of America"):
  - config key ............ snl.lending-workbench.list
  - H1 .................... "Lending workbench"
  - One row per loan account, COMBINING four source tables:
      Loan type ............ SNLLOANACCOUNT → SNLLOANTYPE
      Customer name ........ SNLLOANACCOUNT → customer   (link)
      Loan ................. SNLLOANACCOUNT.ACCOUNTID     (link, filter "Contains")
      Interest ............. SNLLOANTXN (interest txn)     (filter "Equals")
      Interest posting date  SNLLOANTXN                    (date-period dropdown)
      Last invoice ......... SNLLOANINVOICE                (filter "Contains")
      Invoice state ........ SNLLOANINVOICE                (dropdown)
  - Toolbar row-actions: "Reverse" and "Regenerate" (disabled until a row is
    selected) — operate on the selected loan account's interest/invoice.

NOTE: the workbench renders its Interest/Invoice cells via the api-p309 backend;
during exploration that API returned a 500 for some rows ("Some content is
unavailable" / "Unexpected processing error for field indexed"). Assertions on
those cells should tolerate a slow/again-needed load.
"""

from typing import Optional
from ..base_page import BasePage


class LendingWorkbenchPage(BasePage):

    LIST_HEADING = "Lending workbench"

    COLUMNS = [
        "Loan type", "Customer name", "Loan", "Interest",
        "Interest posting date", "Last invoice", "Invoice state",
    ]

    # ── Navigation ──────────────────────────────────────────────────────────────
    def navigate_to_list(self):
        """
        Open Lending Management → Lending workbench.

        Same cross-module switch pattern as the other Lending listers: the
        module trigger link in the top document is labelled after whichever
        module (Lending/Depository Management) is currently active.
        """
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
                const link = document.querySelector('a[href*="lending-workbench.list"]');
                if (link) link.click();
            }"""
        )
        # The workbench aggregates a lot of data and loads slowly — allow extra time.
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=30_000)
        self._wait_for_grid()

    def _wait_for_grid(self):
        """Wait for the grid columns to actually render — the workbench loads its
        data (and headers) noticeably after the H1 appears."""
        try:
            self.frame.get_by_role("columnheader", name="Loan type").first.wait_for(
                state="visible", timeout=30_000)
        except Exception:
            pass
        self.page.wait_for_timeout(1_000)

    def wait_for_list_page(self):
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=30_000)
        self._wait_for_grid()

    # ── Inspection ──────────────────────────────────────────────────────────────
    def get_column_headers(self) -> list[str]:
        self._wait_for_grid()
        headers = self.frame.get_by_role("columnheader").all()
        return [h.inner_text().strip() for h in headers if h.inner_text().strip()]

    def get_first_loan_id(self) -> Optional[str]:
        """Read the first visible loan account id from the 'Loan' column, so
        tests can round-trip the filter against a row the workbench actually
        shows (it lists a filtered subset of all accounts)."""
        info = self.get_first_row_info()
        return info["loan"] if info else None

    def get_first_row_info(self) -> Optional[dict]:
        """First data row as {'loan_type', 'customer', 'loan'} — customer and
        loan are drillable links."""
        rows = self.frame.get_by_role("row")
        for i in range(rows.count()):
            cells = rows.nth(i).get_by_role("gridcell")
            if cells.count() >= 4:  # skips the header row (has columnheaders)
                loan_link = cells.nth(3).get_by_role("link")   # Loan = 4th gridcell
                cust_link = cells.nth(2).get_by_role("link")   # Customer = 3rd gridcell
                if loan_link.count() > 0 and loan_link.first.inner_text().strip():
                    return {
                        "loan_type": cells.nth(1).inner_text().strip(),
                        "customer": cust_link.first.inner_text().strip() if cust_link.count() else "",
                        "loan": loan_link.first.inner_text().strip(),
                    }
        return None

    def _loan_filter(self):
        return self.frame.get_by_role("textbox", name="Loan").first

    def search_by_loan(self, account_id: str):
        """Filter the grid by the 'Loan' (account id) column ('Contains')."""
        box = self._loan_filter()
        box.fill(account_id)
        self.page.wait_for_timeout(300)
        self._loan_filter().press("Enter")
        self.page.wait_for_timeout(1_500)
        for _ in range(16):
            if self.frame.get_by_role("link", name=account_id, exact=True).count() > 0:
                return
            self.page.wait_for_timeout(500)

    def _row_for_loan(self, account_id: str):
        return self.frame.get_by_role("row").filter(
            has=self.frame.get_by_role("link", name=account_id, exact=True)
        ).first

    def is_loan_visible(self, account_id: str) -> bool:
        return self.frame.get_by_role("link", name=account_id, exact=True).count() > 0

    def get_row_values(self, account_id: str) -> dict:
        """Return the loan account's row as {column: cell text}."""
        row = self._row_for_loan(account_id)
        cells = row.get_by_role("gridcell").all()
        texts = [c.inner_text().strip() for c in cells]
        # First gridcell is the "Select row" checkbox cell; the remaining cells
        # line up with COLUMNS.
        values = texts[1:] if texts and not texts[0] else texts
        return dict(zip(self.COLUMNS, values))

    def get_interest(self, account_id: str) -> str:
        return self.get_row_values(account_id).get("Interest", "")

    def get_invoice_state(self, account_id: str) -> str:
        return self.get_row_values(account_id).get("Invoice state", "")

    def get_last_invoice(self, account_id: str) -> str:
        return self.get_row_values(account_id).get("Last invoice", "")

    # ── Row actions ─────────────────────────────────────────────────────────────
    def select_row_by_loan(self, account_id: str):
        self._row_for_loan(account_id).get_by_role("checkbox", name="Select row").check()
        self.page.wait_for_timeout(500)

    def reverse_button(self):
        return self.frame.get_by_role("button", name="Reverse").first

    def regenerate_button(self):
        return self.frame.get_by_role("button", name="Regenerate").first

    def click_reverse(self):
        self.reverse_button().click()
        self.page.wait_for_timeout(1_000)
        self._confirm_if_dialog()

    def click_regenerate(self):
        self.regenerate_button().click()
        self.page.wait_for_timeout(1_000)
        self._confirm_if_dialog()

    def _confirm_if_dialog(self):
        """Reverse/Regenerate may raise a confirmation dialog — click its
        confirming button if present."""
        for name in ("Reverse", "Regenerate", "Confirm", "Yes", "OK", "Continue"):
            btn = self.frame.get_by_role("button", name=name)
            try:
                if btn.count() and btn.last.is_visible():
                    btn.last.click()
                    self.page.wait_for_timeout(1_000)
                    return
            except Exception:
                pass

    # ── Drillable columns (Customer name, Loan are links) ───────────────────────
    def click_loan_drill(self, account_id: str):
        """Click the 'Loan' link → navigates to the loan account record."""
        self._row_for_loan(account_id).get_by_role("gridcell").nth(3) \
            .get_by_role("link").first.click()
        self.page.wait_for_timeout(1_500)

    def click_customer_drill(self, account_id: str):
        """Click the 'Customer name' link → navigates to the customer record."""
        self._row_for_loan(account_id).get_by_role("gridcell").nth(2) \
            .get_by_role("link").first.click()
        self.page.wait_for_timeout(1_500)

    def current_heading(self) -> str:
        h = self.frame.locator("h1").first
        return h.inner_text().strip() if h.count() else ""
