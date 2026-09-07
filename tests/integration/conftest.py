"""
conftest.py — fixtures for end-to-end scenarios that combine UI + API + DB.

  - `db`     : an OracleDB query helper (see integrations/db.py). Session-scoped
               so one connection is reused across the whole run.
  - `bruno`  : a thin handle onto the Bruno CLI runner (see integrations/bruno.py).

Both fixtures **skip** the test (rather than error) when their backend isn't
configured yet, so the rest of the suite keeps running even before the Oracle
credentials / Bruno CLI are set up. Configure them via .env — see
docs/DB_API_INTEGRATION.md.

The session-scoped `authenticated_page` (UI) fixture lives in the parent
tests/conftest.py and is available here automatically.
"""

import pytest

from integrations import db as db_helper
from integrations import bruno as bruno_helper


@pytest.fixture(scope="session")
def db():
    """Oracle query helper, or skip if Oracle isn't configured in .env."""
    if not db_helper.oracle_config_present():
        pytest.skip(
            "Oracle DB not configured — set ORACLE_HOST / ORACLE_SERVICE (or "
            "ORACLE_SID) / ORACLE_USER / ORACLE_PASSWORD in .env "
            "(see docs/DB_API_INTEGRATION.md)."
        )
    conn = db_helper.connect_from_env()
    yield conn
    conn.close()


@pytest.fixture()
def bruno():
    """Bruno CLI runner module, or skip if Bruno isn't configured/installed."""
    if not bruno_helper.bruno_config_present():
        pytest.skip(
            "Bruno not configured — set BRUNO_COLLECTION_DIR in .env and install "
            "the Bruno CLI (npm install -g @usebruno/cli). "
            "See docs/DB_API_INTEGRATION.md."
        )
    return bruno_helper
