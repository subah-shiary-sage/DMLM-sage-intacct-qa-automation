"""
listing_page.py
Page Object for the Depository Account Category **list** page.

Selectors verified against live DOM on 2026-07-15 (DMLM entity):
  - H1 ...................... "Depository account categories"
  - Create ................. button[aria-label="Create"]
  - Name filter ............ input[aria-label="Name"][placeholder="Contains"]
  - Bulk Delete ............ button[aria-label="Delete"]  (disabled until a row is selected)
  - Row name / Edit / More actions per row
  - Setup menu link href contains: snl.depository-category.list
"""

from ..base_page import BasePage


class DepositoryAccountCategoryListingPage(BasePage):

    LIST_HEADING = "Depository account categories"

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to_list(self):
        """Open Depository Management → Setup → Account category."""
        self.navigate_to_module_list(
            module_label="Depository Management",
            href_fragment="depository-category.list",
            list_heading=self.LIST_HEADING,
        )

    # ── Actions ────────────────────────────────────────────────────────────────

    # The Create control is a <button aria-label="Create"> whose ARIA role
    # computes to "link", so target it by aria-label (role-agnostic).
    CREATE_BTN = '[aria-label="Create"]'

    def click_create(self):
        """Click Create and wait for the create form."""
        self.frame.locator(self.CREATE_BTN).first.click()
        self.frame.get_by_role(
            "heading", name="Create depository account category"
        ).wait_for(timeout=10_000)

    def _name_filter(self):
        return self.frame.locator(
            'input[aria-label="Name"][placeholder="Contains"]'
        ).first

    def search_by_name(self, name: str):
        """Type into the Name column filter and submit."""
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
            "heading", name="Depository account category:"
        ).wait_for(timeout=10_000)

    def is_record_visible(self, name: str) -> bool:
        """True if a record link with the exact name is present in the grid."""
        return self.frame.get_by_role("link", name=name, exact=True).count() > 0

    def wait_for_list_page(self):
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=10_000)

    # ── List-page inspection helpers (used by list tests) ─────────────────────

    def get_column_headers(self) -> list[str]:
        headers = self.frame.get_by_role("columnheader").all()
        return [h.inner_text().strip() for h in headers]

    def is_create_visible(self) -> bool:
        return self.frame.locator(self.CREATE_BTN).first.is_visible()

    def bulk_delete_button(self):
        """The toolbar (bulk) Delete button — disabled until a row is selected."""
        return self.frame.get_by_role("button", name="Delete").first

    def select_first_row(self):
        """Tick the first data row's checkbox."""
        self.frame.get_by_role("checkbox", name="Select row").first.check()
        self.page.wait_for_timeout(500)

    def first_row_has_actions(self) -> bool:
        """True if the first data row exposes a 'More actions' control."""
        return self.frame.get_by_role("button", name="More actions").first.is_visible()
