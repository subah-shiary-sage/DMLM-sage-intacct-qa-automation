"""
check_db.py — quick standalone Oracle connectivity check.

Run:  python -m integrations.check_db

Reads the ORACLE_* settings from .env, opens a thin-mode connection, and runs
`SELECT 1 FROM dual`. Prints a clear OK / failure message so you can confirm the
credentials work before wiring them into tests.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level up from this file's package).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from integrations import db as db_helper  # noqa: E402  (after load_dotenv)


def main() -> int:
    if not db_helper.oracle_config_present():
        print(
            "Oracle is not configured yet.\n"
            "Set ORACLE_HOST, ORACLE_SERVICE (or ORACLE_SID), ORACLE_USER and "
            "ORACLE_PASSWORD in .env — see docs/DB_API_INTEGRATION.md."
        )
        return 2

    try:
        conn = db_helper.connect_from_env()
    except Exception as exc:  # connection/auth/network error
        print(f"FAILED to connect to Oracle:\n  {type(exc).__name__}: {exc}")
        return 1

    try:
        value = conn.scalar("SELECT 1 FROM dual")
        if value == 1:
            print("OK — connected to Oracle and ran 'SELECT 1 FROM dual' successfully.")
            return 0
        print(f"Connected, but got an unexpected result: {value!r}")
        return 1
    except Exception as exc:
        print(f"Connected, but the test query failed:\n  {type(exc).__name__}: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
