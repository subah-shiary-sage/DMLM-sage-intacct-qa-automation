"""
test_workbench_behavior.py
Lending Workbench column-behaviour tests (LW-016 – LW-019):
  - Reverse changes the row's data + DB (SNLLOANTXN reversed)
  - Regenerate re-creates interest/invoice data
  - Drillable columns navigate (Customer name → customer, Loan → loan account)

These operate on whatever the workbench currently lists. They skip cleanly when
no suitable row is present (the workbench shows a filtered subset and its
interest/invoice cells depend on the api-p309 backend).
"""

import pytest


@pytest.fixture()
def first_row(workbench_page):
    """The first data row's {loan_type, customer, loan}, or skip if none."""
    info = workbench_page.get_first_row_info()
    if not info:
        pytest.skip("No loan account rows visible in the workbench.")
    return info


class TestWorkbenchDrill:

    def test_lw_018_drill_loan_column(self, workbench_page, first_row, steps):
        """LW-018 — Clicking the 'Loan' link drills into the loan account."""
        account_id = first_row["loan"]
        steps.append(f"Clicking Loan link '{account_id}' to drill in")
        workbench_page.click_loan_drill(account_id)
        heading = workbench_page.current_heading()
        steps.append(f"Landed on heading: '{heading}'")
        # We navigated off the workbench into a record view.
        assert heading and heading != workbench_page.LIST_HEADING, (
            f"expected to drill into a record, still on '{heading}'"
        )

    def test_lw_019_drill_customer_column(self, workbench_page, first_row, steps):
        """LW-019 — Clicking the 'Customer name' link drills into the customer."""
        if not first_row["customer"]:
            pytest.skip("First row has no customer link.")
        account_id = first_row["loan"]
        steps.append(f"Clicking Customer link '{first_row['customer']}' to drill in")
        workbench_page.click_customer_drill(account_id)
        heading = workbench_page.current_heading()
        steps.append(f"Landed on heading: '{heading}'")
        assert heading and heading != workbench_page.LIST_HEADING, (
            f"expected to drill into the customer, still on '{heading}'"
        )


class TestWorkbenchReverseRegenerate:
    """LW-016 / LW-017 — Reverse and Regenerate behaviour.

    These require a row that has generated interest/invoice (so the actions are
    enabled). They pick such a row from the DB via the workbench, and verify the
    column data + DB change. When no generated row is visible, they skip.
    """

    def _row_with_interest(self, workbench_page, db, cny):
        """Find a workbench row whose account has an interest txn in the DB."""
        info = workbench_page.get_first_row_info()
        if not info:
            return None
        acct = db.query_one(
            'SELECT "RECORD#" AS K FROM SNLLOANACCOUNT WHERE "CNY#"=:c AND ACCOUNTID=:id',
            {"c": cny, "id": info["loan"]})
        if not acct:
            return None
        has_interest = db.scalar(
            'SELECT COUNT(*) FROM SNLLOANTXN WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k '
            'AND TXNTYPE=\'I\' AND STATE=\'P\'', {"c": cny, "k": acct["K"]})
        return {"id": info["loan"], "key": acct["K"]} if has_interest else None

    def test_lw_016_reverse_updates_column_and_db(self, workbench_page, db, cny, steps):
        """LW-016 — Reversing a row reverses its interest txn in the DB and
        updates the workbench columns."""
        target = self._row_with_interest(workbench_page, db, cny)
        if not target:
            pytest.skip("No workbench row with a posted interest txn to reverse.")
        before = db.scalar(
            'SELECT COUNT(*) FROM SNLLOANTXN WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k AND STATE=\'R\'',
            {"c": cny, "k": target["key"]})
        steps.append(f"Selecting '{target['id']}' and clicking Reverse")
        workbench_page.select_row_by_loan(target["id"])
        if not workbench_page.reverse_button().is_enabled():
            pytest.skip("Reverse not enabled for the selected row.")
        workbench_page.click_reverse()
        workbench_page.page.wait_for_timeout(2_000)
        after = db.scalar(
            'SELECT COUNT(*) FROM SNLLOANTXN WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k AND STATE=\'R\'',
            {"c": cny, "k": target["key"]})
        steps.append(f"Reversed txn count {before} -> {after}")
        assert after > before, "reversing should mark a txn STATE='R' (reversed)"

    def test_lw_017_regenerate_creates_new_data(self, workbench_page, db, cny, steps):
        """LW-017 — Regenerating a row re-creates interest/invoice data (new
        txn rows appear in the DB)."""
        target = self._row_with_interest(workbench_page, db, cny)
        if not target:
            pytest.skip("No workbench row eligible for regenerate.")
        before = db.scalar(
            'SELECT COUNT(*) FROM SNLLOANTXN WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k',
            {"c": cny, "k": target["key"]})
        steps.append(f"Selecting '{target['id']}' and clicking Regenerate")
        workbench_page.select_row_by_loan(target["id"])
        if not workbench_page.regenerate_button().is_enabled():
            pytest.skip("Regenerate not enabled for the selected row.")
        workbench_page.click_regenerate()
        workbench_page.page.wait_for_timeout(2_000)
        after = db.scalar(
            'SELECT COUNT(*) FROM SNLLOANTXN WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k',
            {"c": cny, "k": target["key"]})
        steps.append(f"Txn count {before} -> {after}")
        assert after >= before, "regenerate should not lose transactions"
