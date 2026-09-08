"""
listing_page.py — Shared base class for module **list** pages.

Every LME/Depository list page (Loan type, Loan account category, Loan fee
type, Loan interest rate, Depository account category, Loan account) renders
the same toolbar/grid shape: a Create button, one or more "Contains" column
filters, a checkbox-select + bulk Delete grid, and an "N items" footer. The
methods below were copy-pasted near-identically into each module's
listing_page.py; they live here so a new module only needs to set the class
constants and override what actually differs (extra filters, a non-Name
lookup key, timing quirks seen live on a specific page).

Subclasses must set:
  - LIST_HEADING    the list page's H1 text
  - CREATE_HEADING  the create form's heading text (defaults to
                     f"Create {LIST_HEADING[:-1].lower()}" if not set —
                     override when that derived guess is wrong)
  - VIEW_HEADING    the record view page's heading prefix, e.g. "Loan type:"

Subclasses must set MODULE_LABEL / HREF_FRAGMENT, or override navigate_to_list
directly when navigation doesn't fit the module-list pattern.
"""

from typing import Optional

from . import locators
from .base_page import BasePage


class ListingPage(BasePage):

    LIST_HEADING: str = ""
    CREATE_HEADING: Optional[str] = None
    VIEW_HEADING: str = ""
    CREATE_BTN = locators.CREATE_BTN

    MODULE_LABEL: str = ""
    HREF_FRAGMENT: str = ""

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to_list(self):
        self.navigate_to_module_list(
            module_label=self.MODULE_LABEL,
            href_fragment=self.HREF_FRAGMENT,
            list_heading=self.LIST_HEADING,
        )

    def wait_for_list_page(self, timeout: int = 10_000):
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=timeout)

    # ── Create ─────────────────────────────────────────────────────────────────

    def is_create_visible(self) -> bool:
        return self.frame.locator(self.CREATE_BTN).first.is_visible()

    def click_create(self, timeout: int = 15_000):
        """Click Create and wait for the create form's heading."""
        heading_name = self.CREATE_HEADING or f"Create {self.LIST_HEADING[:-1].lower()}"
        self.frame.locator(self.CREATE_BTN).first.click()
        self.frame.get_by_role("heading", name=heading_name).wait_for(timeout=timeout)

    # ── Name filter / search (single "Contains" box, most common shape) ────────

    def _name_filter(self):
        """The primary Name/text column filter. Override where the DOM needs
        a more specific selector (aria-label, position among several filters)."""
        return self.frame.locator(locators.CONTAINS_FILTER).first

    def search_by_name(self, name: str, settle_ms: int = 1_500):
        box = self._name_filter()
        box.fill(name)
        box.press("Enter")
        self.page.wait_for_timeout(settle_ms)

    def clear_search(self, settle_ms: int = 1_000):
        box = self._name_filter()
        box.fill("")
        box.press("Enter")
        self.page.wait_for_timeout(settle_ms)

    # ── Row access ─────────────────────────────────────────────────────────────

    def is_record_visible(self, name: str) -> bool:
        return self.frame.get_by_role("link", name=name, exact=True).count() > 0

    def open_record_by_name(self, name: str, timeout: int = 15_000):
        """Click a record's Name link and wait for its View page (auto-searches if needed)."""
        link = self.frame.get_by_role("link", name=name, exact=True)
        if link.count() == 0 or not link.first.is_visible():
            self.search_by_name(name)
            link = self.frame.get_by_role("link", name=name, exact=True)
        link.first.click()
        self.frame.get_by_role("heading", name=self.VIEW_HEADING).wait_for(timeout=timeout)

    def row_names(self) -> list[str]:
        """
        Visible Name-cell values.

        Grid name cells render as links; toolbar/breadcrumb links share the
        same role, so anything that isn't a data row is filtered out by
        label against LIST_HEADING/common chrome text.
        """
        skip = {"create", "edit", self.LIST_HEADING.lower(), ""}
        out = []
        links = self.frame.get_by_role("link")
        for i in range(links.count()):
            text = (links.nth(i).inner_text() or "").strip()
            if text.lower() not in skip:
                out.append(text)
        return out

    def count_rows_named(self, name: str) -> int:
        return sum(1 for n in self.row_names() if n == name)

    # ── List-page inspection helpers ────────────────────────────────────────────

    def get_column_headers(self) -> list[str]:
        headers = self.frame.get_by_role("columnheader").all()
        return [h.inner_text().strip() for h in headers]

    def get_items_count_text(self) -> str:
        """The footer 'N items' text."""
        el = self.frame.get_by_text("items", exact=False)
        return el.first.inner_text() if el.count() else ""

    # ── Bulk selection / delete ────────────────────────────────────────────────

    def bulk_delete_button(self):
        return self.frame.get_by_role("button", name="Delete").first

    def click_bulk_delete(self, settle_ms: int = 1_200):
        self.bulk_delete_button().click()
        self.page.wait_for_timeout(settle_ms)

    def bulk_delete_dialog(self):
        """
        The bulk-delete confirmation modal.

        Located by role only — unlike the single-record modal (see
        BasePage.delete_dialog) it doesn't reliably carry confirmation text
        to filter on.
        """
        return self.frame.locator(locators.DIALOG).last

    def select_first_row(self, settle_ms: int = 500):
        self.frame.get_by_role("checkbox", name="Select row").first.check()
        self.page.wait_for_timeout(settle_ms)

    def select_all_rows(self, settle_ms: int = 500):
        self.frame.get_by_role("checkbox", name="Select all").first.check()
        self.page.wait_for_timeout(settle_ms)

    def select_row_by_name(self, name: str, settle_ms: int = 400) -> bool:
        """Tick the checkbox on the row whose Name is `name`. False if not found."""
        rows = self.frame.get_by_role("row")
        for i in range(rows.count()):
            row = rows.nth(i)
            if (row.inner_text() or "").strip().startswith(("Select row" + name, name)):
                box = row.get_by_role("checkbox")
                if box.count():
                    box.first.check()
                    self.page.wait_for_timeout(settle_ms)
                    return True
        return False

    def selected_count(self) -> int:
        boxes = self.frame.get_by_role("checkbox", name="Select row")
        return sum(1 for i in range(boxes.count()) if boxes.nth(i).is_checked())

    # ── Toast / notification ────────────────────────────────────────────────────

    def toast_text(self) -> str:
        el = self.frame.locator(locators.ALERT_OR_STATUS)
        return el.first.inner_text().strip() if el.count() else ""
