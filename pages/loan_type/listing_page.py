"""
listing_page.py
Page Object for the Loan Type **list** page (Lending Management → Setup → Loan type).

Selectors verified against live DOM 2026-07-15 (entity sit-bob_ocr / DMLM):
  - H1 ...................... "Loan types"
  - Create ................. link[aria-label="Create"]
  - Name filter ............ input[aria-label="Loan type"][placeholder="Contains"]
                              NOTE: the Type (Revolving/Non-revolving) filter column shares the
                              *same* aria-label "Loan type" — it is a combobox, not a textbox,
                              so the [placeholder="Contains"] + role disambiguates them.
  - Bulk Delete ............ button[aria-label="Delete"] (disabled until a row is selected)
  - Setup menu link href contains: loan-type.list
"""

from ..base_page import BasePage


class LoanTypeListingPage(BasePage):

    LIST_HEADING = "Loan types"

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to_list(self):
        """Open Lending Management → Setup → Loan type."""
        self.navigate_to_module_list(
            module_label="Lending Management",
            href_fragment="loan-type.list",
            list_heading=self.LIST_HEADING,
        )

    # ── Actions ────────────────────────────────────────────────────────────────

    CREATE_BTN = '[aria-label="Create"]'

    def click_create(self):
        """Click Create and wait for the create form."""
        self.frame.locator(self.CREATE_BTN).first.click()
        self.frame.get_by_role(
            "heading", name="Create loan type"
        ).wait_for(timeout=10_000)

    def _name_filter(self):
        """The Loan type *name* text filter — disambiguated from the Type combobox filter
        (which shares the same aria-label) by matching the textbox role + Contains placeholder."""
        return self.frame.locator(
            'input[aria-label="Loan type"][placeholder="Contains"]'
        ).first

    def search_by_name(self, name: str):
        box = self._name_filter()
        box.fill(name)
        box.press("Enter")
        self.page.wait_for_timeout(1_500)

    def clear_search(self):
        box = self._name_filter()
        box.fill("")
        box.press("Enter")
        self.page.wait_for_timeout(1_000)

    def open_record_by_name(self, name: str):
        """Click a record's Name link and wait for its View page (auto-searches if needed)."""
        link = self.frame.get_by_role("link", name=name, exact=True)
        if not link.first.is_visible():
            self.search_by_name(name)
        link.first.click()
        self.frame.get_by_role(
            "heading", name="Loan type:"
        ).wait_for(timeout=10_000)

    def is_record_visible(self, name: str) -> bool:
        return self.frame.get_by_role("link", name=name, exact=True).count() > 0

    def wait_for_list_page(self):
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=10_000)

    # ── List-page inspection helpers ────────────────────────────────────────────

    def get_column_headers(self) -> list[str]:
        headers = self.frame.get_by_role("columnheader").all()
        return [h.inner_text().strip() for h in headers]

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
        """The footer 'N items' text."""
        return self.frame.get_by_text("items", exact=False).first.inner_text()
