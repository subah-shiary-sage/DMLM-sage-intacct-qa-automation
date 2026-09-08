"""
listing_page.py
Page Object for the Loan Interest Rate **list** page (Lending Management → Setup → Loan interest rates).

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

from ..listing_page import ListingPage


class LoanInterestRateListingPage(ListingPage):

    LIST_HEADING = "Loan interest rates"
    CREATE_HEADING = "Create loan interest rate"
    VIEW_HEADING = "Loan interest rates:"
    MODULE_LABEL = "Lending Management"
    HREF_FRAGMENT = "loan-interest-rate.list"

    def navigate_to_list(self):
        super().navigate_to_list()
        # The toolbar (Create button, filters) renders a moment after the
        # heading — wait for it so callers can reliably interact immediately.
        self.frame.locator(self.CREATE_BTN).first.wait_for(state="visible", timeout=10_000)

    def click_create(self, timeout: int = 10_000):
        """Click Create and wait for the create form."""
        heading = self.frame.get_by_role("heading", name=self.CREATE_HEADING)
        btn = self.frame.locator(self.CREATE_BTN).first
        btn.wait_for(state="visible", timeout=timeout)
        btn.click()
        try:
            heading.wait_for(timeout=timeout)
        except Exception:
            # Occasionally the first click lands before the button is fully
            # interactive; retry once.
            btn.click()
            heading.wait_for(timeout=timeout)

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
        self.page.wait_for_timeout(1_000)
        # Live-DOM discovery: a record just created and immediately searched
        # for can lag the list's backend index by several seconds — poll
        # generously (~9s total) rather than accept a short fixed wait.
        for _ in range(16):
            if self.frame.get_by_role("link", name=name, exact=True).count() > 0:
                return
            self.page.wait_for_timeout(500)

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
        self.frame.get_by_role("heading", name=self.VIEW_HEADING).wait_for(timeout=10_000)
        # Let the async navigation/hydration settle before returning control
        # (mitigates an intermittent "execution context destroyed" flake).
        self.page.wait_for_timeout(500)

    # ── List-page inspection helpers ────────────────────────────────────────────

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

    def has_raw_column_keys(self) -> bool:
        return any(
            header == "BULK_SELECTED" or header.startswith("IA.") or header.startswith("ROW_")
            for header in self.get_column_headers()
        )
