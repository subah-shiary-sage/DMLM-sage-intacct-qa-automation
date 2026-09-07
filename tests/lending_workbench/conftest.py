"""
conftest.py — Lending Workbench fixtures (UI + API + DB scenario).

  - workbench_page            : the Lending workbench lister POM (UI)
  - loan_account_listing_page : the Loan accounts list POM (UI)
  - db                        : Oracle query helper (skips if unconfigured)
  - loan_api                  : the process-jobs API module (skips if unconfigured)
  - CNY                       : the company id (CNY#) for this environment

Session-wide auth (authenticated_page) + reporting come from the parent
tests/conftest.py.
"""

import os
import pytest

from integrations import db as db_helper
from integrations import loan_api as loan_api_helper


# Company id (CNY#) for p309 / snltahmid1b. Overridable via .env.
CNY_DEFAULT = 30901031134347


@pytest.fixture(scope="session")
def cny() -> int:
    return int(os.environ.get("LENDING_CNY", CNY_DEFAULT))


@pytest.fixture(scope="session")
def db():
    if not db_helper.oracle_config_present():
        pytest.skip("Oracle not configured (see docs/DB_API_INTEGRATION.md).")
    conn = db_helper.connect_from_env()
    yield conn
    conn.close()


@pytest.fixture()
def loan_api():
    if not loan_api_helper.api_config_present():
        pytest.skip(
            "Loan API not configured — set LOAN_API_BASE + LOAN_API_BEARER (or "
            "LOAN_API_COOKIE) in .env, or drive the calls via Bruno."
        )
    return loan_api_helper


@pytest.fixture()
def workbench_page(authenticated_page):
    from pages.lending_workbench.workbench_page import LendingWorkbenchPage
    wb = LendingWorkbenchPage(authenticated_page)
    wb.navigate_to_list()
    return wb


@pytest.fixture()
def loan_account_listing_page(authenticated_page):
    from pages.lending_workbench.loan_account_page import LoanAccountListingPage
    listing = LoanAccountListingPage(authenticated_page)
    listing.navigate_to_list()
    return listing


# ══════════════════════════════════════════════════════════════════════════════
# Statement-run state management
#
# After interest generation the statement run's state flips to 'I' (in progress)
# which LOCKS that period — no further generation can run against it. For the
# tests to stay repeatable we reset the run's state back to 'O' (open) with a
# direct DB update, both before and after use. (Requested behaviour — the DB
# user owns the schema and this is the documented way to re-open a period.)
# ══════════════════════════════════════════════════════════════════════════════

def reset_statement_run_state(db, cny, run_key) -> int:
    """Reset a locked statement run (STATE='I') back to open (STATE='O').
    Returns the number of rows updated."""
    return db.execute(
        'UPDATE SNLLOANSTATEMENTRUN SET STATE = \'O\' '
        'WHERE "CNY#" = :c AND "RECORD#" = :k AND STATE = \'I\'',
        {"c": cny, "k": run_key},
    )


@pytest.fixture()
def statement_run(db, cny):
    """Yield a usable statement run key (SNLLOANSTATEMENTRUN.RECORD#), ensuring
    the period is OPEN before the test and re-opening it afterwards so the next
    run can reuse it."""
    row = db.query_one(
        'SELECT "RECORD#" AS K FROM SNLLOANSTATEMENTRUN WHERE "CNY#" = :c '
        'ORDER BY WHENCREATED DESC FETCH FIRST 1 ROWS ONLY', {"c": cny})
    if not row:
        pytest.skip("No statement run in DB — create one via 'Generate interest and statements'.")
    key = row["K"]
    reset_statement_run_state(db, cny, key)   # ensure open before the test
    yield key
    try:
        reset_statement_run_state(db, cny, key)   # re-open after (interest gen locks it)
    except Exception:
        pass
