"""
loan_api.py — call the Lending "process-jobs" API to generate interest+invoice
and statements for a loan account.

Endpoint (verified from the app / user):
    POST {base}/ia/api/beta/services/loan-management/loan-statements/process-jobs

Payload:
    {
      "loanAccountKey":  "<SNLLOANACCOUNT.RECORD#>",
      "statementRunKey": "<SNLLOANSTATEMENTRUN.RECORD#>",
      "automationStep":  "loanInterest" | "loanStatement",
      "statementPDFTemplate": ""
    }

  - automationStep="loanInterest"  → generates interest AND the invoice
  - automationStep="loanStatement" → generates the statement

Config (.env):
    LOAN_API_BASE   = https://api-p309.intacct.com        # default
    LOAN_API_BEARER = <oauth/bearer token>                # OR
    LOAN_API_COOKIE = <raw Cookie header from an authed session>

Auth note: the workbench UI calls this endpoint using the logged-in Intacct
session. For headless test use you must supply either a bearer token or a
session cookie (whichever your Bruno setup uses). Until one is set,
`api_config_present()` is False so the API-backed tests skip cleanly.

If you prefer to keep driving these calls through Bruno instead, use
integrations/bruno.py with a .bru request and skip this module.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

DEFAULT_BASE = "https://api-p309.intacct.com"
PROCESS_JOBS_PATH = "/ia/api/beta/services/loan-management/loan-statements/process-jobs"


def api_config_present() -> bool:
    """True only if we have somewhere to send and some way to authenticate."""
    base = os.environ.get("LOAN_API_BASE", DEFAULT_BASE)
    has_auth = bool(os.environ.get("LOAN_API_BEARER") or os.environ.get("LOAN_API_COOKIE"))
    return bool(base) and has_auth


def _headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    bearer = os.environ.get("LOAN_API_BEARER")
    cookie = os.environ.get("LOAN_API_COOKIE")
    if bearer:
        h["Authorization"] = f"Bearer {bearer}"
    if cookie:
        h["Cookie"] = cookie
    return h


def _process_job(loan_account_key, statement_run_key, automation_step,
                 statement_pdf_template: str = "", timeout: int = 60) -> requests.Response:
    base = os.environ.get("LOAN_API_BASE", DEFAULT_BASE).rstrip("/")
    url = base + PROCESS_JOBS_PATH
    payload = {
        "loanAccountKey": str(loan_account_key),
        "statementRunKey": str(statement_run_key),
        "automationStep": automation_step,
        "statementPDFTemplate": statement_pdf_template,
    }
    return requests.post(url, json=payload, headers=_headers(), timeout=timeout)


def generate_interest(loan_account_key, statement_run_key,
                      statement_pdf_template: str = "") -> requests.Response:
    """automationStep=loanInterest → interest + invoice generation."""
    return _process_job(loan_account_key, statement_run_key, "loanInterest",
                        statement_pdf_template)


def generate_statement(loan_account_key, statement_run_key,
                       statement_pdf_template: str = "") -> requests.Response:
    """automationStep=loanStatement → statement generation."""
    return _process_job(loan_account_key, statement_run_key, "loanStatement",
                        statement_pdf_template)
