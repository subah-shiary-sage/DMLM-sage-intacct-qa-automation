"""
bruno.py — run your existing Bruno (.bru) API requests from pytest via the
Bruno CLI, so API assertions reuse the collection you already maintain rather
than being re-written in Python.

Prerequisite (one-time): install the Bruno CLI (needs Node.js):

    npm install -g @usebruno/cli

That gives you the `bru` command. This helper shells out to it, captures the
JSON run report, and returns it parsed so a test can assert on the response.

Config (from .env — see docs/DB_API_INTEGRATION.md):

    BRUNO_COLLECTION_DIR=C:\\path\\to\\your\\bruno\\collection
    BRUNO_ENV=your_bruno_env_name      # e.g. "sit" — optional
    BRUNO_CLI=bru                      # optional; override if not on PATH

Usage (via the `bruno` pytest fixture):

    result = bruno.run("Loan Type/Get loan type.bru", vars={"name": name})
    assert result.ok
    body = result.first_response_body()
    assert body["items"][0]["type"] == "Revolving"
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional


class BrunoResult:
    """Parsed output of a single `bru run`."""

    def __init__(self, report: dict, raw_stdout: str, returncode: int):
        self.report = report
        self.raw_stdout = raw_stdout
        self.returncode = returncode

    @property
    def ok(self) -> bool:
        """True if the CLI exited 0 and no request/assertion failed."""
        if self.returncode != 0:
            return False
        summary = self.report.get("summary", {})
        return (
            summary.get("failedRequests", 0) == 0
            and summary.get("failedAssertions", 0) == 0
            and summary.get("failedTests", 0) == 0
        )

    def _results(self) -> list[dict]:
        return self.report.get("results", [])

    def first_response(self) -> Optional[dict]:
        results = self._results()
        if not results:
            return None
        return results[0].get("response", {})

    def first_response_body(self) -> Any:
        """The first request's response body, JSON-decoded when possible."""
        resp = self.first_response() or {}
        data = resp.get("data")
        if isinstance(data, (dict, list)):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (ValueError, TypeError):
                return data
        return data

    def status_code(self) -> Optional[int]:
        resp = self.first_response() or {}
        return resp.get("status")


def bruno_config_present() -> bool:
    """True only if a Bruno collection dir is configured AND the CLI is on
    PATH — lets fixtures skip cleanly when Bruno isn't set up yet."""
    coll = os.environ.get("BRUNO_COLLECTION_DIR")
    if not coll or not Path(coll).is_dir():
        return False
    cli = os.environ.get("BRUNO_CLI", "bru")
    return shutil.which(cli) is not None


def run(request_path: str, *, env: Optional[str] = None,
        vars: Optional[dict] = None) -> BrunoResult:
    """
    Run a single .bru request (path relative to BRUNO_COLLECTION_DIR) and
    return a BrunoResult.

    `vars` are passed as run-time variables (--env-var KEY=VALUE), letting a
    test inject the record name / id it just created in the UI so the Bruno
    request targets that exact record.
    """
    collection = Path(os.environ["BRUNO_COLLECTION_DIR"])
    cli = os.environ.get("BRUNO_CLI", "bru")
    env = env or os.environ.get("BRUNO_ENV")

    out_file = Path(tempfile.mkdtemp(prefix="bruno_")) / "report.json"
    cmd = [cli, "run", request_path, "--output", str(out_file), "--format", "json"]
    if env:
        cmd += ["--env", env]
    for k, v in (vars or {}).items():
        cmd += ["--env-var", f"{k}={v}"]

    proc = subprocess.run(
        cmd, cwd=str(collection), capture_output=True, text=True, timeout=120
    )

    report: dict = {}
    if out_file.exists():
        try:
            report = json.loads(out_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            report = {}

    return BrunoResult(report=report, raw_stdout=proc.stdout, returncode=proc.returncode)
