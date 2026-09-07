"""
listing_page.py
Page Object for the Loan Interest Rate **list** page
(Lending Management → Setup → Loan interest rates).

Selectors verified against live DOM 2026-07-16 (entity sit-bob_ocr / DMLM):
  - H1 ...................... "Loan interest rates"
  - Create ................. link[aria-label="Create"]
  - Name filter ............ input[aria-label="Name"][placeholder="Contains"]
  - "Loan type" column ...... a combobox filter — NOT a separate association;
                               it holds the same Revolving/Non-revolving value
                               as the record's own Type field.
  - Status filter ........... combobox, defaults to "Active"
  - Bulk Delete ............ button[aria-label="Delete"] (disabled until a row is selected)
  - Setup menu link href contains: loan-interest-rate.list
"""

from ..base_page import BasePage


class LoanInterestRateListingPage(BasePage):

    LIST_HEADING = "Loan interest rates"

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to_list(self):
        """Open Lending Management → Setup → Loan interest rates."""
        self.navigate_to_module_list(
            module_label="Lending Management",
            href_fragment="loan-interest-rate.list",
            list_heading=self.LIST_HEADING,
        )
        # The toolbar (Create button, filters) renders a moment after the
        # heading — wait for it so callers can reliably interact immediately.
        self.frame.locator(self.CREATE_BTN).first.wait_for(state="visible", timeout=10_000)

    # ── Actions ────────────────────────────────────────────────────────────────

    CREATE_BTN = '[aria-label="Create"]'

    def click_create(self):
        """Click Create and wait for the create form."""
        heading = self.frame.get_by_role("heading", name="Create loan interest rate")
        btn = self.frame.locator(self.CREATE_BTN).first
        btn.wait_for(state="visible", timeout=10_000)
        btn.click()
        try:
            heading.wait_for(timeout=10_000)
        except Exception:
            # Occasionally the first click lands before the button is fully
            # interactive; retry once.
            btn.click()
            heading.wait_for(timeout=10_000)

    def _name_filter(self):
        return self.frame.locator(
            'input[aria-label="Name"][placeholder="Contains"]'
        ).first

    def search_by_name(self, name: str):
        box = self._name_filter()
        box.fill(name)
        # fill() can trigger a debounced re-render that replaces the input
        # node; re-locate before pressing Enter to avoid a stale-element
        # timeout (seen live as an "elementHandle.press" hang).
        self.page.wait_for_timeout(300)
        self._name_filter().press("Enter")
        # Poll briefly for the grid to finish re-fetching instead of a fixed
        # sleep — larger datasets can take longer than a fixed 1.5s to
        # filter. Returns as soon as the searched name appears; if it's
        # legitimately absent (e.g. verifying a delete), falls through after
        # the full poll window.
        self.page.wait_for_timeout(1_000)
        # Live-DOM discovery: a record just created and immediately searched
        # for can lag the list's backend index by several seconds — poll
        # generously (~9s total) rather than accept a short fixed wait.
        for _ in range(16):
            if self.frame.get_by_role("link", name=name, exact=True).count() > 0:
                return
            self.page.wait_for_timeout(500)

    def clear_search(self):
        box = self._name_filter()
        box.fill("")
        box.press("Enter")
        self.page.wait_for_timeout(1_000)

    def _loan_type_filter(self):
        return self.frame.get_by_role("combobox", name="Loan type").first

    def _status_filter(self):
        return self.frame.get_by_role("combobox", name="Status").first

    def _select_filter_option(self, control, option: str):
        control.click()
        target = self.frame.get_by_role("option", name=option, exact=True)
        try:
            target.first.wait_for(state="visible", timeout=5_000)
            target.first.click()
        except Exception:
            self.frame.get_by_text(option, exact=True).last.click()
        self.page.wait_for_timeout(1_000)

    def filter_by_loan_type(self, loan_type: str):
        self._select_filter_option(self._loan_type_filter(), loan_type)

    def filter_by_status(self, status: str):
        self._select_filter_option(self._status_filter(), status)

    def open_record_by_name(self, name: str):
        """Click a record's Name link and wait for its View page (auto-searches if needed)."""
        link = self.frame.get_by_role("link", name=name, exact=True)
        if not link.first.is_visible():
            self.search_by_name(name)
        link.first.click()
        self.frame.get_by_role(
            "heading", name="Loan interest rates:"
        ).wait_for(timeout=10_000)
        # Let the async navigation/hydration settle before returning control
        # (mitigates an intermittent "execution context destroyed" flake).
        self.page.wait_for_timeout(500)

    def is_record_visible(self, name: str) -> bool:
        return self.frame.get_by_role("link", name=name, exact=True).count() > 0

    def wait_for_list_page(self):
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=10_000)

    # ── List-page inspection helpers ────────────────────────────────────────────

    def get_column_headers(self) -> list[str]:
        headers = self.frame.get_by_role("columnheader").all()
        return [h.inner_text().strip() for h in headers]

    def row_names(self) -> list[str]:
        """Visible record names from linked Name cells."""
        rows = self.frame.get_by_role("row")
        names = []
        for index in range(1, rows.count()):
            links = rows.nth(index).get_by_role("link")
            if links.count():
                value = (links.first.inner_text() or "").strip()
                if value:
                    names.append(value)
        return names

    def visible_data_rows(self):
        return self.frame.get_by_role("row").locator("xpath=position()>1")

    def is_create_visible(self) -> bool:
        return self.frame.locator(self.CREATE_BTN).first.is_visible()

    def bulk_delete_button(self):
        return self.frame.get_by_role("button", name="Delete").first

    def select_first_row(self):
        self.frame.get_by_role("checkbox", name="Select row").first.check()
        self.page.wait_for_timeout(500)

    def select_all_rows(self):
        self.frame.get_by_role("checkbox", name="Select all").first.check()
        self.page.wait_for_timeout(500)

    def get_items_count_text(self) -> str:
        items = self.frame.get_by_text("items", exact=False)
        return items.first.inner_text() if items.count() else ""

    def has_raw_column_keys(self) -> bool:
        return any(
            header == "BULK_SELECTED" or header.startswith("IA.") or header.startswith("ROW_")
            for header in self.get_column_headers()
        )
