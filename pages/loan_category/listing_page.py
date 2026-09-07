"""
listing_page.py
Page Object for the Loan account category **list** page
(Lending Management → Setup → Loan account categories).

NOTE: this is a different object from ``pages/depository_category`` — that one
covers *Depository* account categories in the Depository Management module.
This one is the Lending Management object behind the "Loan Category - CRUD"
checklist.

Selectors captured against the live app 2026-08-17
(release www-p303 / SNL_release_monthly / LME entity):
  - Menu href fragment .... snl.loan-category.list  (label "Loan account categories")
  - H1 .................... "Loan account categories"
  - Create ................ [aria-label="Create"]
  - Grid columns .......... BULK_SELECTED (untranslated key — Bug #43), Name,
                            Document sequence
  - Column filters ........ two input[placeholder="Contains"] (Name, Document sequence)
"""

from ..base_page import BasePage


class LoanCategoryListingPage(BasePage):

    LIST_HEADING = "Loan account categories"
    CREATE_BTN = '[aria-label="Create"]'
    CREATE_HEADING = "Create loan account category"

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to_list(self):
        self.navigate_to_module_list(
            module_label="Lending Management",
            href_fragment="loan-category.list",
            list_heading=self.LIST_HEADING,
        )

    def wait_for_list_page(self, timeout: int = 15_000):
        self.frame.get_by_role("heading", name=self.LIST_HEADING).wait_for(timeout=timeout)

    def click_create(self):
        self.frame.locator(self.CREATE_BTN).first.click()
        self.frame.get_by_role("heading", name=self.CREATE_HEADING).wait_for(timeout=15_000)

    def is_create_visible(self) -> bool:
        return self.frame.locator(self.CREATE_BTN).first.is_visible()

    # ── Filtering / row access ─────────────────────────────────────────────────

    def _name_filter(self):
        """The Name column filter — the first of the two 'Contains' boxes."""
        return self.frame.locator('input[placeholder="Contains"]').first

    def _doc_seq_filter(self):
        """The Document sequence column filter — the second 'Contains' box."""
        return self.frame.locator('input[placeholder="Contains"]').nth(1)

    def search_by_name(self, name: str):
        box = self._name_filter()
        box.fill(name)
        box.press("Enter")
        self.page.wait_for_timeout(1_500)

    def search_by_document_sequence(self, value: str):
        box = self._doc_seq_filter()
        box.fill(value)
        box.press("Enter")
        self.page.wait_for_timeout(1_500)

    def clear_search(self):
        for box in (self._name_filter(), self._doc_seq_filter()):
            if box.count():
                box.fill("")
                box.press("Enter")
        self.page.wait_for_timeout(1_200)

    def get_column_headers(self) -> list[str]:
        return [h.inner_text().strip() for h in self.frame.get_by_role("columnheader").all()]

    def row_names(self) -> list[str]:
        """
        Visible Name-cell values.

        Grid name cells render as links; toolbar/breadcrumb links share the same
        role, so anything that isn't a data row is filtered out by label.
        """
        skip = {"create", self.LIST_HEADING.lower(), "edit", ""}
        out = []
        links = self.frame.get_by_role("link")
        for i in range(links.count()):
            text = (links.nth(i).inner_text() or "").strip()
            if text.lower() not in skip:
                out.append(text)
        return out

    def count_rows_named(self, name: str) -> int:
        return sum(1 for n in self.row_names() if n == name)

    def is_record_visible(self, name: str) -> bool:
        return self.frame.get_by_role("link", name=name, exact=True).count() > 0

    def open_record_by_name(self, name: str):
        link = self.frame.get_by_role("link", name=name, exact=True)
        if link.count() == 0 or not link.first.is_visible():
            self.search_by_name(name)
            link = self.frame.get_by_role("link", name=name, exact=True)
        link.first.click()
        # The view heading is the plural noun + record ID (see the POM docstring).
        self.frame.get_by_role("heading", name="Loan account categories:").wait_for(
            timeout=15_000
        )

    def get_items_count_text(self) -> str:
        el = self.frame.get_by_text("items", exact=False)
        return el.first.inner_text() if el.count() else ""

    # ── Bulk selection ─────────────────────────────────────────────────────────

    def select_row_by_name(self, name: str) -> bool:
        rows = self.frame.get_by_role("row")
        for i in range(rows.count()):
            row = rows.nth(i)
            if (row.inner_text() or "").strip().startswith(("Select row" + name, name)):
                box = row.get_by_role("checkbox")
                if box.count():
                    box.first.check()
                    self.page.wait_for_timeout(400)
                    return True
        return False

    def selected_count(self) -> int:
        boxes = self.frame.get_by_role("checkbox", name="Select row")
        return sum(1 for i in range(boxes.count()) if boxes.nth(i).is_checked())

    def bulk_delete_button(self):
        return self.frame.get_by_role("button", name="Delete").first

    def toast_text(self) -> str:
        el = self.frame.locator('[role="alert"], [role="status"]')
        return el.first.inner_text().strip() if el.count() else ""
