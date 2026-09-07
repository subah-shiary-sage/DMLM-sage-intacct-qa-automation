"""
test_example_combined.py — a worked example of a single scenario that spans
all three layers: UI (Playwright) + API (Bruno CLI) + DB (Oracle).

This is a TEMPLATE. The Bruno request path, the SQL, and the exact field names
below are placeholders — adjust them to your real collection and schema. Until
Oracle and Bruno are configured in .env the `db` / `bruno` fixtures skip, so
this file is safe to keep in the suite from day one.

Pattern
-------
1. UI   — create a Loan Type through the browser (existing page objects).
2. API  — run the Bruno request that fetches it; assert the response.
3. DB   — query Oracle directly; assert the row landed with the right state.

Three independent layers of evidence for one user action. The same fixtures
also support the reverse direction (seed via DB/API, then verify in the UI).
"""

import pytest

from pages.loan_type.listing_page import LoanTypeListingPage
from pages.loan_type.type_page import LoanTypePage

# Same verified picker values used by tests/loan_type/test_create.py.
ORDER_ENTRY_TXN_DEF = "Loan management invoicing"
PRINCIPAL_ITEM      = "p01--Loan principal item"
INTEREST_ITEM       = "i01--Loan interest item"


@pytest.mark.integration
def test_loan_type_ui_api_db_end_to_end(
    bruno, db, authenticated_page, unique_loan_type_name, steps
):
    """End-to-end: create a Loan Type in the UI, then confirm it via the Bruno
    API request AND a direct Oracle query.

    `bruno` and `db` are requested first so that, when they're not configured
    yet, the test skips before the (expensive) browser login runs."""
    name = unique_loan_type_name

    # ── 1) UI — create through the browser ───────────────────────────────────
    listing = LoanTypeListingPage(authenticated_page)
    listing.navigate_to_list()
    listing.click_create()
    lt = LoanTypePage(authenticated_page)
    lt.fill_name(name)
    lt.select_type("Revolving")
    lt.set_interest_type("Compound")
    lt.set_interest_calculation_method("Actual/365")
    lt.set_order_entry_transaction_definition("loan", ORDER_ENTRY_TXN_DEF)
    lt.set_item_for_principal_posting("loan", PRINCIPAL_ITEM)
    lt.set_item_for_interest_posting("interest", INTEREST_ITEM)
    lt.click_add_row()
    lt.set_row_sort_order("1")
    lt.set_row_type("Interest")
    steps.append(f"Created Loan Type '{name}' through the UI")
    lt.save()
    lt.wait_for_view_page()

    # ── 2) API — run the Bruno request that looks it up ──────────────────────
    #    Adjust the .bru path to your collection; `vars` injects the new name
    #    so the request targets exactly this record.
    result = bruno.run("Loan Type/Get loan type.bru", vars={"name": name})
    steps.append("Ran the Bruno 'Get loan type' request for the new record")
    assert result.ok, f"Bruno request failed: {result.raw_stdout}"
    body = result.first_response_body()
    assert body, "Bruno returned an empty body"
    # e.g. assert body["items"][0]["type"] == "Revolving"  # match your API shape

    # ── 3) DB — assert the row exists in Oracle with the right state ─────────
    #    Adjust table/column names to your real schema.
    row = db.query_one(
        "SELECT status FROM loantype WHERE name = :name", {"name": name}
    )
    steps.append("Queried Oracle to confirm the row persisted")
    assert row is not None, f"No loantype row found in Oracle for '{name}'"
    # e.g. assert row["STATUS"] == "active"   # Oracle folds columns to UPPER

    # ── Cleanup ──────────────────────────────────────────────────────────────
    lt.click_delete()
    lt.confirm_delete_in_modal()
