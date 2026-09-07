"""Secure Jira Data Center REST access backed by Windows DPAPI.

The PAT is never accepted on the command line and is never printed. Run
``scripts/setup-jira-access.ps1`` once to create the current-user encrypted
credential outside the repository.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import json
import os
import re
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


ENTROPY = b"SageIntacctQA:JiraPAT:v1"
DEFAULT_CREDENTIAL_PATH = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "SageIntacctQA" / "jira-auth.json"
)
ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")


class JiraAccessError(RuntimeError):
    """A safe-to-display Jira access error."""


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob(data: bytes) -> tuple[_DataBlob, Any]:
    buffer = ctypes.create_string_buffer(data)
    pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    return _DataBlob(len(data), pointer), buffer


def _dpapi_unprotect(ciphertext: bytes) -> str:
    if os.name != "nt":
        raise JiraAccessError("Jira credentials can only be decrypted on Windows.")

    encrypted_blob, encrypted_buffer = _blob(ciphertext)
    entropy_blob, entropy_buffer = _blob(ENTROPY)
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL

    ok = crypt32.CryptUnprotectData(
        ctypes.byref(encrypted_blob),
        None,
        ctypes.byref(entropy_blob),
        None,
        None,
        0,
        ctypes.byref(output_blob),
    )
    # Keep input buffers alive until the Windows call is complete.
    _ = encrypted_buffer, entropy_buffer
    if not ok:
        raise JiraAccessError(
            "Unable to decrypt the Jira credential for the current Windows account. "
            "Run scripts/setup-jira-access.ps1 again."
        )

    try:
        plaintext = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return plaintext.decode("utf-8")
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _validate_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise JiraAccessError("The configured Jira URL must be an absolute HTTPS URL.")
    return value


def _validate_issue_key(value: str) -> str:
    value = value.strip().upper()
    if not ISSUE_KEY_RE.fullmatch(value):
        raise JiraAccessError(f"Invalid Jira issue key: {value!r}")
    return value


def load_encrypted_credential(path: Path = DEFAULT_CREDENTIAL_PATH) -> tuple[str, str]:
    if not path.exists():
        raise JiraAccessError(
            "Jira credential is not installed. Run scripts/setup-jira-access.ps1."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if payload.get("version") != 1:
            raise ValueError("unsupported credential version")
        base_url = _validate_base_url(str(payload["jira_url"]))
        encrypted = base64.b64decode(payload["protected_pat"], validate=True)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise JiraAccessError(
            "The Jira credential file is invalid. Run scripts/setup-jira-access.ps1 again."
        ) from exc

    token = _dpapi_unprotect(encrypted).strip()
    if not token:
        raise JiraAccessError("The decrypted Jira credential is empty.")
    return base_url, token


class JiraPatClient:
    def __init__(self, base_url: str, token: str, *, timeout: int = 20):
        self.base_url = _validate_base_url(base_url)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        )

    @classmethod
    def from_encrypted_store(cls, *, timeout: int = 20) -> "JiraPatClient":
        base_url, token = load_encrypted_credential()
        return cls(base_url, token, timeout=timeout)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/rest/api/2/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        try:
            response = self.session.request(
                method, self._url(path), timeout=self.timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise JiraAccessError(
                f"Jira request failed for {method} {path}: {exc.__class__.__name__}"
            ) from exc
        if not response.ok:
            raise JiraAccessError(
                f"Jira request failed for {method} {path}: HTTP {response.status_code}"
            )
        return response

    def verify(self) -> dict[str, Any]:
        return self._request("GET", "myself").json()

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        issue_key = _validate_issue_key(issue_key)
        return self._request(
            "GET",
            f"issue/{issue_key}",
            params={
                "expand": "names,schema,renderedFields,changelog",
                "fields": "*all",
            },
        ).json()

    def get_comments(self, issue_key: str) -> dict[str, Any]:
        issue_key = _validate_issue_key(issue_key)
        return self._request(
            "GET",
            f"issue/{issue_key}/comment",
            params={"startAt": 0, "maxResults": 1000, "expand": "renderedBody"},
        ).json()

    def get_remote_links(self, issue_key: str) -> list[dict[str, Any]]:
        issue_key = _validate_issue_key(issue_key)
        return self._request("GET", f"issue/{issue_key}/remotelink").json()

    def collect_issue(self, issue_key: str) -> dict[str, Any]:
        issue_key = _validate_issue_key(issue_key)
        issue = self.get_issue(issue_key)
        source_status: dict[str, str] = {
            "issue": "Reviewed",
            "comments": "Reviewed",
            "remote_links": "Reviewed",
        }
        blockers: list[str] = []

        comments: dict[str, Any] = {}
        remote_links: list[dict[str, Any]] = []
        try:
            comments = self.get_comments(issue_key)
        except JiraAccessError as exc:
            source_status["comments"] = "Blocked"
            blockers.append(str(exc))
        try:
            remote_links = self.get_remote_links(issue_key)
        except JiraAccessError as exc:
            source_status["remote_links"] = "Blocked"
            blockers.append(str(exc))

        return {
            "jira_url": f"{self.base_url}/browse/{issue_key}",
            "issue_key": issue_key,
            "source_status": source_status,
            "blockers": blockers,
            "issue": issue,
            "comments": comments,
            "remote_links": remote_links,
        }

    def download_attachments(
        self, issue_payload: dict[str, Any], destination: Path
    ) -> list[Path]:
        destination.mkdir(parents=True, exist_ok=True)
        attachments = issue_payload.get("fields", {}).get("attachment", []) or []
        saved: list[Path] = []
        for attachment in attachments:
            content_url = str(attachment.get("content", ""))
            filename = Path(str(attachment.get("filename", "attachment"))).name
            if not content_url or not filename:
                continue
            try:
                response = self.session.get(
                    content_url, timeout=self.timeout, allow_redirects=True
                )
            except requests.RequestException as exc:
                raise JiraAccessError(
                    f"Attachment download failed for {filename}: {exc.__class__.__name__}"
                ) from exc
            if not response.ok:
                raise JiraAccessError(
                    f"Attachment download failed for {filename}: HTTP {response.status_code}"
                )
            target = destination / filename
            target.write_bytes(response.content)
            saved.append(target)
        return saved

    def add_comment(self, issue_key: str, body: str) -> str:
        issue_key = _validate_issue_key(issue_key)
        if not body.strip():
            raise JiraAccessError("Jira comment body cannot be empty.")
        response = self._request(
            "POST", f"issue/{issue_key}/comment", json={"body": body}
        ).json()
        return str(response.get("id", ""))

    def attach_file(self, issue_key: str, file_path: Path) -> list[str]:
        issue_key = _validate_issue_key(issue_key)
        file_path = file_path.resolve()
        if not file_path.is_file():
            raise JiraAccessError(f"Attachment does not exist: {file_path}")
        headers = {"X-Atlassian-Token": "no-check"}
        with file_path.open("rb") as handle:
            response = self._request(
                "POST",
                f"issue/{issue_key}/attachments",
                headers=headers,
                files={"file": (file_path.name, handle)},
            ).json()
        return [str(item.get("filename", "")) for item in response]


def _require_write_confirmation(value: bool) -> None:
    if not value:
        raise JiraAccessError(
            "Write blocked. Re-run only after user approval with --confirm-write."
        )


def _default_output(issue_key: str) -> Path:
    return Path("outputs") / "jira" / issue_key / "jira-intake.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="Verify the encrypted Jira credential.")

    collect = subparsers.add_parser("collect", help="Collect one Jira issue package.")
    collect.add_argument("issue_key")
    collect.add_argument("--output", type=Path)
    collect.add_argument("--download-attachments", action="store_true")

    comment = subparsers.add_parser("comment", help="Post an approved Jira comment.")
    comment.add_argument("issue_key")
    comment.add_argument("--body-file", type=Path, required=True)
    comment.add_argument("--confirm-write", action="store_true")

    attach = subparsers.add_parser("attach", help="Upload an approved Jira attachment.")
    attach.add_argument("issue_key")
    attach.add_argument("file", type=Path)
    attach.add_argument("--confirm-write", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = JiraPatClient.from_encrypted_store()
        if args.command == "verify":
            profile = client.verify()
            display_name = profile.get("displayName") or profile.get("name") or "user"
            print(f"Jira access verified for {display_name} at {client.base_url}.")
            return 0

        if args.command == "collect":
            issue_key = _validate_issue_key(args.issue_key)
            payload = client.collect_issue(issue_key)
            output = args.output or _default_output(issue_key)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Saved Jira intake package: {output.resolve()}")
            if args.download_attachments:
                saved = client.download_attachments(
                    payload["issue"], output.parent / "attachments"
                )
                print(f"Downloaded {len(saved)} attachment(s).")
            return 0

        if args.command == "comment":
            _require_write_confirmation(args.confirm_write)
            body = args.body_file.read_text(encoding="utf-8")
            comment_id = client.add_comment(args.issue_key, body)
            print(f"Posted approved Jira comment {comment_id}.")
            return 0

        if args.command == "attach":
            _require_write_confirmation(args.confirm_write)
            filenames = client.attach_file(args.issue_key, args.file)
            print("Uploaded approved Jira attachment(s): " + ", ".join(filenames))
            return 0
    except (JiraAccessError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
