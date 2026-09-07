"""
test_workbench_lister.py
UI tests for the Lending Workbench lister (LW-001 – LW-004).
These need only the UI (no API/DB), so they run as soon as p309 login works.
Verified against live DOM 2026-07-21.
"""

import pytest
from playwright.sync_api import expect

from pages.lending_workbench.workbench_page import LendingWorkbenchPage


class TestLendingWorkbenchLister:

    def test_lw_001_lister_loads(self, workbench_page, steps):
        """LW-001 — Lending workbench lister loads with its heading."""
        steps.append("Navigated to Lending Management > Lending workbench")
        expect(
            workbench_page.frame.get_by_role("heading", name=workbench_page.LIST_HEADING)
        ).to_be_visible()

    def test_lw_002_columns_present(self, workbench_page, steps):
        """LW-002 — Grid shows the combined columns from the 4 source tables."""
        steps.append("Read the workbench grid column headers")
        headers = " ".join(workbench_page.get_column_headers()).lower()
        for col in ["loan type", "customer name", "loan", "interest",
                    "last invoice", "invoice state"]:
            assert col in headers, f"missing column '{col}' in: {headers}"

    def test_lw_003_reverse_regenerate_disabled_by_default(self, workbench_page, steps):
        """LW-004 — Reverse/Regenerate are disabled with no row selected."""
        steps.append("Checked toolbar with no rows selected")
        expect(workbench_page.reverse_button()).to_be_disabled()
        expect(workbench_page.regenerate_button()).to_be_disabled()

    def test_lw_004_filter_by_loan(self, workbench_page, steps):
        """LW-003 — Filtering by a loan account id shows that row.

        The account id is read from the workbench itself (it lists a filtered
        subset of all loan accounts), so the filter is exercised round-trip
        against a row we know is present."""
        account_id = workbench_page.get_first_loan_id()
        if not account_id:
            pytest.skip("No loan accounts visible in the workbench.")
        steps.append(f"Filtering workbench by Loan = '{account_id}'")
        workbench_page.search_by_loan(account_id)
        assert workbench_page.is_loan_visible(account_id), (
            f"'{account_id}' should be visible after filtering"
        )
