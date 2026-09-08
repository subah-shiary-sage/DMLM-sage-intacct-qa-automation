"""
jira_client.py — Append defects to the running LME bug comment on JIRA.

All LME defects live in ONE append-only comment (IADSSL-1714, comment 4855245).
Filing a bug means: GET the whole body, append a '----'-delimited wiki-markup
block, PUT the whole body back. Attachments are uploaded separately and then
embedded into that bug's block.

Both the append and the embed are idempotent — re-running a scenario must not
produce a duplicate block or a duplicate image.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

import requests

from .config import JiraTarget

# JIRA wiki markup uses CRLF; mixing bare \n corrupts list rendering.
NL = "\r\n"


class JiraError(RuntimeError):
    """A JIRA API call failed."""


def build_bug_block(
    *,
    bug_no: int,
    area: str,
    title: str,
    steps: Sequence[str],
    observed: Sequence[str],
    expected: Sequence[str],
    screenshot_filename: str | None = None,
) -> str:
    """
    Render one bug in the IADSSL-1714 house format.

    The leading space on ' # ' / ' * ' markers and the blank line before each
    '*...:*' heading are both load-bearing — without them JIRA swallows the
    list into the preceding paragraph.
    """
    title = title.strip()
    if not title.endswith("."):
        title += "."

    lines: list[str] = ["----", f"h3. Bug #{bug_no} [{area}]: {title}", ""]

    lines.append("*Steps to reproduce:*")
    lines.extend(f" # {s}" for s in steps)
    lines.append("")

    lines.append("*Observed behavior:*")
    lines.extend(f" * {s}" for s in observed)
    lines.append("")

    lines.append("*Expected behavior:*")
    lines.extend(f" * {s}" for s in expected)

    if screenshot_filename:
        lines += ["", "*Screenshot:*", f"!{screenshot_filename}!"]

    return NL.join(lines)


class JiraClient:
    def __init__(self, base_url: str, token: str, *, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout

    @classmethod
    def from_target(cls, target: JiraTarget, *, timeout: int = 30) -> "JiraClient":
        """Build a client, resolving the token from the env var the config names."""
        return cls(target.base_url, target.resolve_token(), timeout=timeout)

    # ── plumbing ───────────────────────────────────────────────────────────────

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/rest/api/2/{path.lstrip('/')}"

    def _check(self, resp: requests.Response, what: str) -> requests.Response:
        if not resp.ok:
            # Never echo headers — they carry the bearer token.
            raise JiraError(f"{what} failed: HTTP {resp.status_code} {resp.text[:400]}")
        return resp

    # ── comment body ───────────────────────────────────────────────────────────

    def get_comment_body(self, issue: str, comment_id: str) -> str:
        resp = self._check(
            requests.get(
                self._url(f"issue/{issue}/comment/{comment_id}"),
                headers=self._headers,
                timeout=self.timeout,
            ),
            f"GET comment {issue}/{comment_id}",
        )
        return resp.json().get("body", "")

    def put_comment_body(self, issue: str, comment_id: str, body: str) -> None:
        self._check(
            requests.put(
                self._url(f"issue/{issue}/comment/{comment_id}"),
                headers=self._headers,
                json={"body": body},
                timeout=self.timeout,
            ),
            f"PUT comment {issue}/{comment_id}",
        )

    @staticmethod
    def bug_numbers_in(body: str) -> list[int]:
        return [int(n) for n in re.findall(r"Bug #(\d+)", body)]

    def next_bug_number_in_comment(self, issue: str, comment_id: str) -> int:
        nums = self.bug_numbers_in(self.get_comment_body(issue, comment_id))
        return (max(nums) + 1) if nums else 1

    # ── filing a bug ───────────────────────────────────────────────────────────

    def append_bug(
        self,
        *,
        issue: str,
        comment_id: str,
        area: str,
        title: str,
        steps: Sequence[str],
        observed: Sequence[str],
        expected: Sequence[str],
        screenshot_filename: str | None = None,
        bug_no: int | None = None,
    ) -> int:
        """
        Append one bug block and return the number it was filed under.

        Idempotent on title: if a block with this exact title already exists, its
        existing number is returned and nothing is posted.
        """
        body = self.get_comment_body(issue, comment_id)

        existing = self._find_bug_by_title(body, title)
        if existing is not None:
            return existing

        nums = self.bug_numbers_in(body)
        number = bug_no if bug_no is not None else ((max(nums) + 1) if nums else 1)

        block = build_bug_block(
            bug_no=number,
            area=area,
            title=title,
            steps=steps,
            observed=observed,
            expected=expected,
            screenshot_filename=screenshot_filename,
        )
        self.put_comment_body(issue, comment_id, body.rstrip("\r\n") + NL + block)
        return number

    @staticmethod
    def _find_bug_by_title(body: str, title: str) -> int | None:
        needle = title.strip().rstrip(".").lower()
        for match in re.finditer(r"h3\. Bug #(\d+) \[[^\]]*\]:\s*(.+)", body):
            if match.group(2).strip().rstrip(".").lower() == needle:
                return int(match.group(1))
        return None

    # ── attachments ────────────────────────────────────────────────────────────

    def attach_screenshot(self, issue: str, file_path: Path) -> str:
        """Upload a file to the issue and return the filename JIRA stored it as."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise JiraError(f"Screenshot not found: {file_path}")

        headers = {
            "Authorization": f"Bearer {self._token}",
            "X-Atlassian-Token": "no-check",
        }
        with file_path.open("rb") as fh:
            resp = self._check(
                requests.post(
                    self._url(f"issue/{issue}/attachments"),
                    headers=headers,
                    files={"file": (file_path.name, fh, "image/png")},
                    timeout=self.timeout,
                ),
                f"attach {file_path.name}",
            )
        payload = resp.json()
        return payload[0]["filename"] if payload else file_path.name

    def existing_attachments(self, issue: str) -> set[str]:
        resp = self._check(
            requests.get(
                self._url(f"issue/{issue}?fields=attachment"),
                headers=self._headers,
                timeout=self.timeout,
            ),
            f"GET attachments for {issue}",
        )
        items = resp.json().get("fields", {}).get("attachment", []) or []
        return {a.get("filename", "") for a in items}

    def embed_screenshot_in_bug(
        self, issue: str, comment_id: str, bug_no: int, filename: str
    ) -> bool:
        """
        Splice ``!<filename>!`` into that bug's block. Returns True if the body
        changed.

        Skips silently when the embed is already present, so re-runs don't
        duplicate the image.
        """
        body = self.get_comment_body(issue, comment_id)
        start = re.search(rf"h3\. Bug #{bug_no} \[", body)
        if not start:
            raise JiraError(f"Bug #{bug_no} not found in comment {comment_id}")

        nxt = re.search(r"\r?\n----", body[start.end():])
        end = start.end() + nxt.start() if nxt else len(body)
        block = body[start.start():end]

        if f"!{filename}!" in block:
            return False

        if "*Screenshot:*" in block:
            new_block = re.sub(r"\*Screenshot:\*(\r?\n!.*?!)?", f"*Screenshot:*{NL}!{filename}!", block, count=1)
        else:
            new_block = block.rstrip("\r\n") + f"{NL}{NL}*Screenshot:*{NL}!{filename}!"

        self.put_comment_body(issue, comment_id, body[:start.start()] + new_block + body[end:])
        return True

    def file_defect(
        self,
        target: JiraTarget,
        *,
        area: str,
        title: str,
        steps: Sequence[str],
        observed: Sequence[str],
        expected: Sequence[str],
        screenshot: Path | None = None,
    ) -> int:
        """
        File one defect end to end: append the block, then upload and embed its
        screenshot. Returns the bug number.

        Ordering matters — the block is posted first so the number is fixed and
        confirmed by JIRA before anything else references it.
        """
        filename = screenshot.name if screenshot else None
        bug_no = self.append_bug(
            issue=target.issue,
            comment_id=target.comment_id,
            area=area,
            title=title,
            steps=steps,
            observed=observed,
            expected=expected,
            screenshot_filename=filename,
        )
        if screenshot:
            if screenshot.name not in self.existing_attachments(target.issue):
                self.attach_screenshot(target.issue, screenshot)
            self.embed_screenshot_in_bug(
                target.issue, target.comment_id, bug_no, screenshot.name
            )
        return bug_no
