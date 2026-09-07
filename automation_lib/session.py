"""
session.py — Logged-in Sage Intacct browser session, usable outside pytest.

The login and optional entity-switch flow used to live only in tests/conftest.py's
``authenticated_page`` fixture. It is here so both pytest and the standalone
regression runner drive the same code path.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Classic Intacct login form field names (stable across releases).
SEL_COMPANY = 'input[name=".company"]'
SEL_USER = 'input[name=".login"]'
SEL_PASSWORD = 'input[name=".passwd"]'
IFRAME = "iframe#iamain"


@dataclass
class SessionConfig:
    app_url: str
    company_id: str
    user_id: str
    password: str
    headless: bool = False
    # Empty means remain at Top level. Set ENTITY_LABEL only when a Jira
    # explicitly requires execution in another entity.
    entity_label: str = ""
    module_entry: str = "Depository Management"
    viewport_width: int = 1680
    viewport_height: int = 1000

    @classmethod
    def from_env(cls) -> "SessionConfig":
        return cls(
            app_url=os.environ["APP_URL"],
            company_id=os.environ["COMPANY_ID"],
            user_id=os.environ["USER_ID"],
            password=os.environ["PASSWORD"],
            headless=os.environ.get("HEADLESS", "false").lower() == "true",
            entity_label=os.environ.get("ENTITY_LABEL", "").strip(),
            module_entry=os.environ.get("MODULE_ENTRY", "Depository Management"),
        )


class LoginFailed(RuntimeError):
    """Login did not reach the app — bad credentials, or the environment is down."""


@dataclass
class AuthenticatedSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page
    config: Optional["SessionConfig"] = None
    # False when the Playwright instance was passed in by the caller (e.g. pytest's
    # session-scoped `pw` fixture), which owns its own lifecycle.
    _owns_playwright: bool = True

    def describe_environment(self) -> str:
        """
        Where this session actually is, for the workbook's evidence note.

        Derived from the live URL rather than a configured label, so a run
        against a dev sandbox can never be recorded as if it were release.
        """
        host = urlparse(self.page.url).netloc or "unknown-host"
        parts = [host]
        if self.config:
            parts.append(self.config.company_id)
            if self.config.entity_label:
                parts.append(f"{self.config.entity_label} entity")
        return ", ".join(parts)

    def close(self) -> None:
        self.context.close()
        self.browser.close()
        if self._owns_playwright:
            self.playwright.stop()

    def __enter__(self) -> "AuthenticatedSession":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


def start_authenticated_session(
    config: SessionConfig, playwright: Playwright | None = None
) -> AuthenticatedSession:
    """
    Log in, optionally switch entity, open the starting module, and return the live session.

    Verified against the live app on 2026-07-15:
      1. Log in with the classic Intacct login form.
      2. Remain at Top level by default. When ENTITY_LABEL is explicitly set,
         switch entity and follow the new browser tab when one opens.
      3. Enter the starting module so its top-nav menu is available. Page objects'
         navigate_to_module_list() switch between modules from whatever we land in.
    """
    owns_playwright = playwright is None
    pw = playwright or sync_playwright().start()

    browser = pw.chromium.launch(headless=config.headless)
    context = browser.new_context(
        viewport={"width": config.viewport_width, "height": config.viewport_height}
    )
    page = context.new_page()

    # ── 1. Login ──────────────────────────────────────────────────────────────
    page.goto(config.app_url, wait_until="load", timeout=30_000)
    page.wait_for_selector(SEL_COMPANY, timeout=15_000)
    page.fill(SEL_COMPANY, config.company_id)
    page.fill(SEL_USER, config.user_id)
    page.fill(SEL_PASSWORD, config.password)
    page.evaluate("document.querySelector('#retbutton').click()")
    try:
        page.wait_for_url("**/frameset.phtml**", timeout=30_000)
    except Exception:
        message = ""
        try:
            body = page.inner_text("body")
            for line in body.splitlines():
                line = line.strip()
                if line and ("incorrect" in line.lower() or "timed out" in line.lower()):
                    message = line
                    break
        except Exception:
            pass
        browser.close()
        if owns_playwright:
            pw.stop()
        detail = f"  page said: {message}\n" if message else ""
        raise LoginFailed(
            f"Login did not reach the app at {config.app_url}\n"
            f"  company={config.company_id} user={config.user_id}\n"
            f"{detail}"
            "  Check APP_URL / COMPANY_ID / USER_ID / PASSWORD in .env, "
            "and that the environment is up."
        )
    page.wait_for_timeout(3_000)

    # ── 2. Optional entity switch (Top level is the default) ──────────────────
    entity_btn = page.get_by_role("button", name="Top level")
    if config.entity_label and entity_btn.count() > 0:
        entity_btn.first.click()
        page.wait_for_timeout(500)
        try:
            with context.expect_page(timeout=15_000) as new_tab:
                page.get_by_role("link", name=config.entity_label).click()
            page = new_tab.value
        except Exception:
            # Some builds switch in-place instead of opening a tab.
            page.get_by_role("link", name=config.entity_label).click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3_000)

    # ── 3. Enter the starting module ──────────────────────────────────────────
    # Best-effort: if we're already inside a module (or the link isn't found) the
    # top-nav menu still handles navigation.
    try:
        page.frame_locator(IFRAME).get_by_role(
            "link", name=config.module_entry
        ).first.click(timeout=10_000)
        page.wait_for_timeout(3_000)
    except Exception:
        pass

    return AuthenticatedSession(
        playwright=pw,
        browser=browser,
        context=context,
        page=page,
        config=config,
        _owns_playwright=owns_playwright,
    )
