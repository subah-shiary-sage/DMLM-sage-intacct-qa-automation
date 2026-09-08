"""
listing_page.py
Page Object for the Loan fee type **list** page
(Lending Management → Setup → Loan fee type).

Selectors captured against the live app 2026-08-12
(release www-p303 / SNL_release_monthly / LME entity):
  - H1 .................... "Loan fee types"
  - Create ................ [aria-label="Create"]
  - Name filter ........... input[placeholder="Contains"]
  - Bulk Delete ........... button "Delete" (disabled until a row is selected)
  - Grid columns .......... BULK_SELECTED (untranslated key — Bug #43), Name, Status
  - Setup menu href contains: loan-fee-type.list
"""

from ..listing_page import ListingPage


class LoanFeeTypeListingPage(ListingPage):

    LIST_HEADING = "Loan fee types"
    VIEW_HEADING = "Loan fee type:"
    MODULE_LABEL = "Lending Management"
    HREF_FRAGMENT = "loan-fee-type.list"
