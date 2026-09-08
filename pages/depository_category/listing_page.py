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

from ..listing_page import ListingPage


class DepositoryAccountCategoryListingPage(ListingPage):

    LIST_HEADING = "Depository account categories"
    CREATE_HEADING = "Create depository account category"
    VIEW_HEADING = "Depository account category:"
    MODULE_LABEL = "Depository Management"
    HREF_FRAGMENT = "depository-category.list"

    def _name_filter(self):
        return self.frame.locator(
            'input[aria-label="Name"][placeholder="Contains"]'
        ).first

    def first_row_has_actions(self) -> bool:
        """True if the first data row exposes a 'More actions' control."""
        return self.frame.get_by_role("button", name="More actions").first.is_visible()
