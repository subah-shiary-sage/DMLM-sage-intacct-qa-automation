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

from .. import locators
from ..listing_page import ListingPage


class LoanCategoryListingPage(ListingPage):

    LIST_HEADING = "Loan account categories"
    CREATE_HEADING = "Create loan account category"
    VIEW_HEADING = "Loan account categories:"
    MODULE_LABEL = "Lending Management"
    HREF_FRAGMENT = "loan-category.list"

    # ── Filtering ──────────────────────────────────────────────────────────────
    # This module has two "Contains" filters (Name, Document sequence); the
    # base class's _name_filter() already targets the first one by position.

    def _doc_seq_filter(self):
        """The Document sequence column filter — the second 'Contains' box."""
        return self.frame.locator(locators.CONTAINS_FILTER).nth(1)

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
