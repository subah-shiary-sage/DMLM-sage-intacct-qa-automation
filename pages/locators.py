"""
locators.py — Selector fragments shared across multiple page objects.

Only fragments that repeat *across modules* live here (e.g. every list page's
Create button, every grid's "Contains" filters, the app's iframe wrapper).
A selector used by a single module (a specific field's aria-label, a
module-only button) stays local to that module's page object — centralizing
it here would just move the duplication instead of removing it.
"""

# Sage Intacct embeds all application content inside this iframe.
IFRAME = "iframe#iamain"

# ── Common controls ──────────────────────────────────────────────────────────
CREATE_BTN = '[aria-label="Create"]'
DELETE_BTN = '[aria-label="Delete"]'
MORE_ACTIONS_BTN = '[aria-label="More actions"]'
CONTAINS_FILTER = 'input[placeholder="Contains"]'

# ── Dialogs / notifications ──────────────────────────────────────────────────
DIALOG = '[role="dialog"]'
ALERT_OR_STATUS = '[role="alert"], [role="status"]'

# The delete confirmation modal is located by this body text — its
# [role="dialog"] wrapper has a zero-size bounding box, so visibility-based
# locators don't work on it.
DELETE_DIALOG_TEXT = "will be permanently deleted"
