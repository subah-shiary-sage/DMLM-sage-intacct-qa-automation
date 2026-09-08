"""
Post the Loan reports findings (bugs #89-#95) as a NEW comment on IADSSL-1714,
and upload the seven screenshots so the !file.png! embeds resolve.

This is deliberately a NEW comment, not an append to the running comment 4855245.

Run:
    set JIRA_API_TOKEN=<token>      (or put JIRA_API_TOKEN=... in .env)
    python Regression/post_loan_reports_comment.py            # dry run
    python Regression/post_loan_reports_comment.py --post     # actually post
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BODY_FILE = ROOT / "Regression" / "IADSSL-1714_loan_reports_comment.txt"
SHOTS_DIR = ROOT / "LME_Loan_Reports_Evidence"

ISSUE = "IADSSL-1714"
BASE_URL = "https://jira.sage.com"
TOKEN_ENV = "JIRA_API_TOKEN"
NL = "\r\n"


def load_dotenv() -> None:
    for name in (".env",):
        p = ROOT / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def token() -> str:
    load_dotenv()
    t = os.environ.get(TOKEN_ENV, "").strip()
    if not t:
        sys.exit(
            f"No JIRA token. Set {TOKEN_ENV} in your environment or in .env "
            "(it must not be committed)."
        )
    return t


def headers(tok: str) -> dict:
    return {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def check(resp: requests.Response, what: str) -> requests.Response:
    if not resp.ok:
        sys.exit(f"{what} failed: HTTP {resp.status_code} {resp.text[:400]}")
    return resp


def existing_bug_numbers(tok: str) -> list[int]:
    """Every 'Bug #N' already used anywhere in the issue's comments."""
    url = f"{BASE_URL}/rest/api/2/issue/{ISSUE}/comment?maxResults=1000"
    data = check(requests.get(url, headers=headers(tok), timeout=30), "GET comments").json()
    nums: list[int] = []
    for c in data.get("comments", []):
        nums += [int(n) for n in re.findall(r"Bug #(\d+)", c.get("body", ""))]
    return sorted(set(nums))


def attach(tok: str, path: Path) -> str:
    h = {"Authorization": f"Bearer {tok}", "X-Atlassian-Token": "no-check"}
    with path.open("rb") as fh:
        resp = check(
            requests.post(
                f"{BASE_URL}/rest/api/2/issue/{ISSUE}/attachments",
                headers=h,
                files={"file": (path.name, fh, "image/png")},
                timeout=120,
            ),
            f"upload {path.name}",
        )
    return resp.json()[0]["filename"]


def main() -> None:
    do_post = "--post" in sys.argv

    body = BODY_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\n", NL)
    shots = sorted(re.findall(r"!([^!\r\n]+\.png)!", body))

    missing = [s for s in shots if not (SHOTS_DIR / s).exists()]
    if missing:
        sys.exit("Missing screenshot files:\n  " + "\n  ".join(missing))

    planned = sorted(int(n) for n in re.findall(r"Bug #(\d+)", body))
    print(f"Comment body : {BODY_FILE}  ({len(body)} chars)")
    print(f"Bugs in body : {planned}")
    print(f"Screenshots  : {len(shots)}, all present in {SHOTS_DIR.name}/")

    if not do_post:
        tok = os.environ.get(TOKEN_ENV, "").strip()
        if tok:
            used = existing_bug_numbers(tok)
            print(f"Bug numbers already on {ISSUE}: max = {max(used) if used else 0}")
            clash = sorted(set(planned) & set(used))
            print("Clashing numbers:", clash if clash else "none")
        print("\nDRY RUN — nothing posted. Re-run with --post to publish.")
        return

    tok = token()

    used = existing_bug_numbers(tok)
    clash = sorted(set(planned) & set(used))
    if clash:
        sys.exit(
            f"Bug numbers {clash} are already used on {ISSUE}. "
            f"Highest existing is {max(used)}. Renumber the body file and re-run."
        )

    for s in shots:
        stored = attach(tok, SHOTS_DIR / s)
        print(f"  uploaded {stored}")

    resp = check(
        requests.post(
            f"{BASE_URL}/rest/api/2/issue/{ISSUE}/comment",
            headers=headers(tok),
            json={"body": body},
            timeout=60,
        ),
        "POST comment",
    )
    cid = resp.json().get("id")
    print(f"\nPosted new comment {cid} on {ISSUE}")
    print(f"  {BASE_URL}/browse/{ISSUE}?focusedCommentId={cid}")


if __name__ == "__main__":
    main()
