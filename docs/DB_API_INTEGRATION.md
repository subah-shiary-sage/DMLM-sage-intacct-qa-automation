# Combined scenarios — UI + API (Bruno) + DB (Oracle)

This project can run a single test that exercises **all three layers**:

| Layer | Tool | In the test |
|-------|------|-------------|
| UI | Playwright | `authenticated_page` fixture + page objects |
| API | your existing **Bruno** `.bru` requests, driven via the Bruno CLI | `bruno` fixture |
| DB | **Oracle** (the DB you query in PhpStorm), via the `oracledb` thin driver | `db` fixture |

A combined scenario is just a normal pytest test that uses all three fixtures —
see [`tests/integration/test_example_combined.py`](../tests/integration/test_example_combined.py).

Until you fill in the config below, the `db` and `bruno` fixtures **skip**
automatically, so the rest of the suite is unaffected.

---

## 1. Oracle DB setup

The driver (`oracledb`) runs in **thin mode** — pure Python, **no Oracle client
install needed**. You only need host, port, and service name (or SID).

### Where to find those values in PhpStorm

1. Open the **Database** tool window (View → Tool Windows → Database).
2. Right-click your Oracle data source → **Properties** (or press `F4`).
3. On the **General** tab you'll see either:
   - **Host**, **Port** (default `1521`), and **Service** — copy these into
     `ORACLE_HOST`, `ORACLE_PORT`, `ORACLE_SERVICE`; **or**
   - a **SID** instead of a service name — use `ORACLE_SID` instead of
     `ORACLE_SERVICE`.
   - The **User** is shown here too; the password is what you type when PhpStorm
     connects.
4. Alternatively click the **URL** field — a JDBC URL like
   `jdbc:oracle:thin:@//dbhost.example.com:1521/ORCLPDB1` gives you everything:
   `dbhost.example.com` → host, `1521` → port, `ORCLPDB1` → service
   (a URL with `:SID` at the end, e.g. `...:1521:ORCL`, means use `ORACLE_SID`).

### Put them in `.env`

```
ORACLE_HOST=dbhost.example.com
ORACLE_PORT=1521
ORACLE_SERVICE=ORCLPDB1          # OR: ORACLE_SID=ORCL
ORACLE_USER=your_db_user
ORACLE_PASSWORD=your_db_password
```

### "Not sure how it's reachable"

The tests run on **this machine**. They connect straight to `ORACLE_HOST:PORT`,
the same way PhpStorm does — so if PhpStorm connects without an SSH tunnel, the
tests will too. If PhpStorm's data source has an **SSH/SSL** tab configured with
a tunnel, the DB is only reachable through that tunnel; tell me and we'll either
open the tunnel before the run or point `oracledb` through it. Quick check:
Properties → **SSH/SSL** tab — if "Use SSH tunnel" is ticked, we need it.

### Verify the connection

```
python -m integrations.check_db
```

(that helper is below — it just opens a connection and runs `SELECT 1 FROM dual`).

---

## 2. Bruno CLI setup

We keep your existing Bruno collection and run its requests from pytest.

1. Install Node.js (if not already), then the Bruno CLI:
   ```
   npm install -g @usebruno/cli
   ```
   This gives you the `bru` command (`bru --version` to confirm).
2. Point `.env` at your collection folder (the directory containing the `.bru`
   files / `bruno.json`):
   ```
   BRUNO_COLLECTION_DIR=C:\path\to\your\bruno\collection
   BRUNO_ENV=sit
   ```
   `BRUNO_ENV` is the Bruno environment name (the dropdown in the Bruno app).

The `bruno` fixture runs a request like this:

```python
result = bruno.run("Loan Type/Get loan type.bru", vars={"name": name})
assert result.ok
body = result.first_response_body()
```

- The path is **relative to `BRUNO_COLLECTION_DIR`**.
- `vars=` injects run-time variables (`--env-var`) so a request can target the
  exact record the UI step just created.

---

## 3. Running combined scenarios

```
# just the integration scenarios:
run_tests.bat -m integration

# everything except them:
run_tests.bat -m "not integration"

# a single combined test:
run_tests.bat tests\integration\test_example_combined.py
```

If Oracle/Bruno aren't configured yet, those tests report as **skipped** (with a
message telling you what's missing) instead of failing.

---

## 4. How a combined test is structured

```python
def test_x_ui_api_db(authenticated_page, bruno, db, unique_loan_type_name, steps):
    name = unique_loan_type_name

    # 1) UI  — create through the browser (existing page objects)
    ...page object calls...  save()

    # 2) API — the Bruno request that fetches it
    result = bruno.run("Loan Type/Get loan type.bru", vars={"name": name})
    assert result.ok

    # 3) DB  — confirm the row persisted in Oracle
    row = db.query_one("SELECT status FROM loantype WHERE name = :name", {"name": name})
    assert row["STATUS"] == "active"   # Oracle folds column names to UPPER case
```

Three independent layers of evidence for one user action. It also works in
reverse: seed a row via `db.execute(...)` or a Bruno request, then verify it
appears in the UI.

> **Note on Oracle column casing:** unquoted identifiers come back UPPER-CASE
> (`row["STATUS"]`, not `row["status"]`). Bind variables use `:name` syntax
> (not `%s`).
