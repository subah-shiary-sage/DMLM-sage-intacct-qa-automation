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

from ..listing_page import ListingPage


class LoanTypeListingPage(ListingPage):

    LIST_HEADING = "Loan types"
    VIEW_HEADING = "Loan type:"
    MODULE_LABEL = "Lending Management"
    HREF_FRAGMENT = "loan-type.list"

    def _name_filter(self):
        """The Loan type *name* text filter — disambiguated from the Type combobox filter
        (which shares the same aria-label) by matching the textbox role + Contains placeholder."""
        return self.frame.locator(
            'input[aria-label="Loan type"][placeholder="Contains"]'
        ).first
