"""
db.py — thin Oracle helper for tests that assert against the database directly
(the same DB you query in PhpStorm).

Uses python-oracledb in **thin mode**: a pure-Python driver that talks to
Oracle over the network with NO Oracle Instant Client / TNS install required.
You only need the host, port, and service name (or SID) — the same values
PhpStorm uses in its data-source settings (see docs/DB_API_INTEGRATION.md for
exactly where to find them).

Connection details are read from environment variables (.env), so no
credentials live in the code:

    ORACLE_HOST=your-db-host
    ORACLE_PORT=1521
    ORACLE_SERVICE=your_service_name     # OR set ORACLE_SID instead
    ORACLE_USER=your_user
    ORACLE_PASSWORD=your_password

Typical use (via the `db` pytest fixture):

    row = db.query_one("SELECT status FROM loantype WHERE name = :name",
                       {"name": some_name})
    assert row["STATUS"] == "active"
"""

from __future__ import annotations

import os
from typing import Any, Optional

import oracledb


class OracleDB:
    """A minimal query helper around a single oracledb connection.

    Queries return rows as dicts keyed by UPPER-CASE column name (Oracle folds
    unquoted identifiers to upper case), so `row["STATUS"]` — not
    `row["status"]`.
    """

    def __init__(self, connection: "oracledb.Connection"):
        self._conn = connection

    # ── Reads ────────────────────────────────────────────────────────────────
    def query(self, sql: str, params: Optional[dict | list] = None) -> list[dict]:
        """Run a SELECT and return all rows as a list of dicts."""
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params or {})
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            cur.close()

    def query_one(self, sql: str, params: Optional[dict | list] = None) -> Optional[dict]:
        """Run a SELECT and return the first row as a dict, or None."""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: Optional[dict | list] = None) -> Any:
        """Return the first column of the first row (e.g. a COUNT(*))."""
        row = self.query_one(sql, params)
        if row is None:
            return None
        return next(iter(row.values()))

    def exists(self, sql: str, params: Optional[dict | list] = None) -> bool:
        """True if the SELECT returns at least one row."""
        return self.query_one(sql, params) is not None

    # ── Writes (for seeding/cleanup in setup scenarios) ──────────────────────
    def execute(self, sql: str, params: Optional[dict | list] = None) -> int:
        """Run an INSERT/UPDATE/DELETE and commit. Returns affected row count."""
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params or {})
            self._conn.commit()
            return cur.rowcount
        finally:
            cur.close()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def _dsn_from_env() -> str:
    """Build an oracledb DSN ("host:port/service" or "host:port/sid") from env."""
    host = os.environ["ORACLE_HOST"]
    port = os.environ.get("ORACLE_PORT", "1521")
    service = os.environ.get("ORACLE_SERVICE")
    sid = os.environ.get("ORACLE_SID")
    if service:
        return oracledb.makedsn(host, int(port), service_name=service)
    if sid:
        return oracledb.makedsn(host, int(port), sid=sid)
    raise RuntimeError(
        "Set either ORACLE_SERVICE or ORACLE_SID in your environment/.env"
    )


def oracle_config_present() -> bool:
    """True only if the minimum Oracle env vars are set — lets fixtures skip
    (rather than error) when the DB isn't configured yet."""
    have_host = bool(os.environ.get("ORACLE_HOST"))
    have_target = bool(os.environ.get("ORACLE_SERVICE") or os.environ.get("ORACLE_SID"))
    have_creds = bool(os.environ.get("ORACLE_USER") and os.environ.get("ORACLE_PASSWORD"))
    return have_host and have_target and have_creds


def connect_from_env() -> OracleDB:
    """Open an Oracle connection using .env settings and wrap it in OracleDB."""
    conn = oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=_dsn_from_env(),
    )
    return OracleDB(conn)
