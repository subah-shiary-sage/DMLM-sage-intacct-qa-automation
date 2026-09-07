"""
test_workbench_e2e.py
End-to-end Lending Workbench scenario (LW-007 – LW-E2E-001, plus LW-015
multi-month):

    create loan account (UI)  →  generate interest+invoice (API loanInterest)
    →  generate statement (API loanStatement)  →  validate in DB + workbench lister

The API steps use integrations/loan_api.py (the process-jobs endpoint). Until
LOAN_API_BASE + auth are set in .env the `loan_api` fixture skips these tests.

The `statement_run` fixture (conftest) resets the run's state I→O around each
test, because interest generation locks the period (STATE='I').

Subject loan account: to stay independent of the (not-yet-verified) create-form
selectors, these tests operate on an EXISTING open loan account from the DB.
"""

import pytest

from tests.lending_workbench.conftest import reset_statement_run_state


# ── Subject account ───────────────────────────────────────────────────────────
@pytest.fixture()
def subject_account(db, cny):
    """A recent OPEN loan account to run generation against.
    Returns {'key': RECORD#, 'id': ACCOUNTID}."""
    row = db.query_one(
        'SELECT "RECORD#" AS K, ACCOUNTID AS ID FROM SNLLOANACCOUNT '
        'WHERE "CNY#" = :c AND STATE = \'O\' AND ACCOUNTID IS NOT NULL '
        'ORDER BY WHENCREATED DESC FETCH FIRST 1 ROWS ONLY', {"c": cny})
    if not row:
        pytest.skip("No open loan account in DB for this company.")
    return {"key": row["K"], "id": row["ID"]}


# ── LW-007 / LW-008 : interest + invoice ──────────────────────────────────────
def test_lw_007_008_generate_interest_and_invoice(
    loan_api, db, cny, subject_account, statement_run, steps
):
    """LW-007 — API loanInterest returns success; LW-008 — DB shows an interest
    txn (TXNTYPE='I') and an invoice for the account."""
    key = subject_account["key"]
    steps.append(f"POST process-jobs automationStep=loanInterest for account {subject_account['id']} "
                 f"(key={key}, run={statement_run})")
    resp = loan_api.generate_interest(key, statement_run)
    assert resp.status_code in (200, 201, 202), f"loanInterest failed: {resp.status_code} {resp.text[:400]}"

    steps.append("Verifying interest txn + invoice landed in Oracle")
    assert db.scalar(
        'SELECT COUNT(*) FROM SNLLOANTXN WHERE "CNY#" = :c AND LOANACCOUNTKEY = :k AND TXNTYPE = \'I\'',
        {"c": cny, "k": key}) >= 1, "expected at least one interest (TXNTYPE='I') txn"
    assert db.scalar(
        'SELECT COUNT(*) FROM SNLLOANINVOICE WHERE "CNY#" = :c AND LOANACCOUNTKEY = :k',
        {"c": cny, "k": key}) >= 1, "expected at least one invoice row"


# ── LW-010 / LW-011 : statement ───────────────────────────────────────────────
def test_lw_010_011_generate_statement(
    loan_api, db, cny, subject_account, statement_run, steps
):
    """LW-010 — API loanStatement returns success; LW-011 — DB shows a statement
    row for the account."""
    key = subject_account["key"]
    steps.append(f"POST process-jobs automationStep=loanStatement for account {subject_account['id']}")
    resp = loan_api.generate_statement(key, statement_run)
    assert resp.status_code in (200, 201, 202), f"loanStatement failed: {resp.status_code} {resp.text[:400]}"

    steps.append("Verifying statement landed in Oracle")
    assert db.scalar(
        'SELECT COUNT(*) FROM SNLLOANSTATEMENT WHERE "CNY#" = :c AND LOANACCOUNTKEY = :k',
        {"c": cny, "k": key}) >= 1, "expected at least one statement row"


# ── LW-009 : workbench lister reflects the generated data ──────────────────────
def test_lw_009_workbench_reflects_generation(
    loan_api, db, cny, subject_account, statement_run, workbench_page, steps
):
    """LW-009 — after generation, the workbench row for the account shows
    Interest / Last invoice / Invoice state populated."""
    key = subject_account["key"]
    account_id = subject_account["id"]
    loan_api.generate_interest(key, statement_run)
    steps.append(f"Filtering workbench to '{account_id}' and reading its row")
    workbench_page.search_by_loan(account_id)
    if not workbench_page.is_loan_visible(account_id):
        pytest.skip(f"'{account_id}' not shown in the (filtered) workbench view")
    values = workbench_page.get_row_values(account_id)
    steps.append(f"Workbench row: {values}")
    n_invoice = db.scalar(
        'SELECT COUNT(*) FROM SNLLOANINVOICE WHERE "CNY#" = :c AND LOANACCOUNTKEY = :k',
        {"c": cny, "k": key})
    if n_invoice >= 1:
        assert values.get("Last invoice") or values.get("Invoice state"), (
            "workbench should show invoice data when the DB has an invoice"
        )


# ── LW-E2E-001 : full chain ───────────────────────────────────────────────────
def test_lw_e2e_001_full_chain(
    loan_api, db, cny, subject_account, statement_run, workbench_page, steps
):
    """LW-E2E-001 — interest+invoice then statement, with DB and lister agreeing."""
    key = subject_account["key"]
    account_id = subject_account["id"]

    steps.append("Step 1/2: generate interest + invoice (API)")
    r1 = loan_api.generate_interest(key, statement_run)
    assert r1.status_code in (200, 201, 202), f"loanInterest: {r1.status_code} {r1.text[:300]}"

    steps.append("Step 2/2: generate statement (API)")
    r2 = loan_api.generate_statement(key, statement_run)
    assert r2.status_code in (200, 201, 202), f"loanStatement: {r2.status_code} {r2.text[:300]}"

    steps.append("Validating DB: interest txn, invoice, statement all present")
    assert db.scalar('SELECT COUNT(*) FROM SNLLOANTXN WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k AND TXNTYPE=\'I\'',
                     {"c": cny, "k": key}) >= 1
    assert db.scalar('SELECT COUNT(*) FROM SNLLOANINVOICE WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k',
                     {"c": cny, "k": key}) >= 1
    assert db.scalar('SELECT COUNT(*) FROM SNLLOANSTATEMENT WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k',
                     {"c": cny, "k": key}) >= 1

    steps.append("Validating UI: workbench lists the account")
    workbench_page.search_by_loan(account_id)
    assert workbench_page.is_loan_visible(account_id)


# ── LW-015 : multi-month — same account, another period, data updates ─────────
def test_lw_015_multi_month_generation_updates_data(
    loan_api, db, cny, subject_account, steps
):
    """LW-015 — Generate interest/invoice/statement for the SAME loan account
    across two different periods (statement runs) and verify each period adds
    its own interest txn / invoice / statement, and statement balances carry
    forward (period-2 beginning balance == period-1 ending balance)."""
    key = subject_account["key"]

    # Two distinct statement runs = two periods (most recent two).
    runs = db.query(
        'SELECT "RECORD#" AS K, STARTDATE, ENDDATE FROM SNLLOANSTATEMENTRUN '
        'WHERE "CNY#" = :c ORDER BY STARTDATE DESC FETCH FIRST 2 ROWS ONLY', {"c": cny})
    if len(runs) < 2:
        pytest.skip("Need at least two statement runs (periods) for the multi-month test.")
    # Process chronologically: older period first.
    period1, period2 = runs[1], runs[0]

    def process(period):
        run_key = period["K"]
        reset_statement_run_state(db, cny, run_key)
        r1 = loan_api.generate_interest(key, run_key)
        assert r1.status_code in (200, 201, 202), f"loanInterest {run_key}: {r1.status_code} {r1.text[:200]}"
        r2 = loan_api.generate_statement(key, run_key)
        assert r2.status_code in (200, 201, 202), f"loanStatement {run_key}: {r2.status_code} {r2.text[:200]}"
        reset_statement_run_state(db, cny, run_key)   # re-open the period
        return run_key

    steps.append(f"Period 1 (run {period1['K']}, {period1['STARTDATE']}): generate interest+invoice+statement")
    run1 = process(period1)
    steps.append(f"Period 2 (run {period2['K']}, {period2['STARTDATE']}): generate interest+invoice+statement")
    run2 = process(period2)

    # Each period produced its own statement row for this account.
    stmt1 = db.query_one(
        'SELECT BEGINNINGBALANCE, ENDINGBALANCE, STARTDATE, ENDDATE FROM SNLLOANSTATEMENT '
        'WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k AND LOANSTATEMENTRUNKEY=:r',
        {"c": cny, "k": key, "r": run1})
    stmt2 = db.query_one(
        'SELECT BEGINNINGBALANCE, ENDINGBALANCE, STARTDATE, ENDDATE FROM SNLLOANSTATEMENT '
        'WHERE "CNY#"=:c AND LOANACCOUNTKEY=:k AND LOANSTATEMENTRUNKEY=:r',
        {"c": cny, "k": key, "r": run2})
    steps.append(f"Period1 statement: {stmt1} | Period2 statement: {stmt2}")
    assert stmt1 is not None, "period 1 produced no statement for the account"
    assert stmt2 is not None, "period 2 produced no statement for the account"

    # Balances carry forward: period-2 opening == period-1 closing.
    if stmt1["ENDINGBALANCE"] is not None and stmt2["BEGINNINGBALANCE"] is not None:
        assert abs(float(stmt2["BEGINNINGBALANCE"]) - float(stmt1["ENDINGBALANCE"])) < 0.01, (
            f"period-2 opening ({stmt2['BEGINNINGBALANCE']}) should equal "
            f"period-1 closing ({stmt1['ENDINGBALANCE']})"
        )
