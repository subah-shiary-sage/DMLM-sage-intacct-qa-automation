"""
integrations/ — cross-system helpers used by end-to-end test scenarios that
combine more than just the UI:

  - db.py     : query the Oracle database directly (the same DB you inspect in
                PhpStorm) via the `oracledb` thin driver — no Oracle client
                install required.
  - bruno.py  : run your existing Bruno (.bru) API requests via the Bruno CLI
                and read their results, so API assertions reuse the collection
                you already maintain instead of being re-implemented in Python.

A "combined" scenario (UI + API + DB) is just a normal pytest test that uses
the `authenticated_page` (UI), `bruno` (API), and `db` (DB) fixtures together.
See tests/integration/test_example_combined.py.
"""
