"""
base_page.py — Shared base class for all Page Object Model pages.
Provides frame access, common waits, navigation, header actions, delete-modal
and picker helpers.

The header-action / delete-dialog / picker / module-nav helpers below were
originally copy-pasted into each module's page objects. They live here so a new
module doesn't need another copy — the DOM quirks they work around are the same
across every LME page.
"""

from typing import Optional

from playwright.sync_api import Locator, Page, FrameLocator

# Sage Intacct embeds all application content inside this iframe.
IFRAME = "iframe#iamain"

# The delete confirmation modal is located by this body text — its
# [role="dialog"] wrapper has a zero-size bounding box, so visibility-based
# locators don't work on it.
DELETE_DIALOG_TEXT = "will be permanently deleted"


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.frame: FrameLocator = page.frame_locator(IFRAME)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded")

    def wait_for_url_contains(self, fragment: str, timeout: int = 10_000):
        self.page.wait_for_url(f"**{fragment}**", timeout=timeout)

    def navigate_to_module_list(
        self,
        *,
        module_label: str,
        href_fragment: str,
        list_heading: str,
        timeout: int = 15_000,
    ):
        """
        Open <module_label> → Setup → the list whose menu href contains
        <href_fragment>, then wait for <list_heading>.

        The module menu lives in the top-level document (outside the content
        iframe). Its trigger link is labelled after whichever app module is
        *currently* active. If the target module is already active, one click
        reveals the Setup submenu directly; otherwise a second click on the
        target label inside the freshly revealed app-switcher list is needed to
        actually switch modules.
        """
        page = self.page

        heading = self.frame.get_by_role("heading", name=list_heading)

        def click_target() -> bool:
            return page.evaluate(
                """(fragment) => {
                    const link = document.querySelector(`a[href*="${fragment}"]`);
                    if (!link) return false;
                    link.click();
                    return true;
                }""",
                href_fragment,
            )

        def open_module_menu():
            page.evaluate(
                """(target) => {
                    const byText = (t) => Array.from(document.querySelectorAll('a'))
                        .find(a => a.textContent.trim() === t
                                && (a.getAttribute('href') || '').startsWith('javascript:void'));
                    const wanted = byText(target);
                    if (wanted) { wanted.click(); return; }
                    const other = Array.from(document.querySelectorAll('a'))
                        .find(a => /Management$/.test(a.textContent.trim())
                                && (a.getAttribute('href') || '').startsWith('javascript:void'));
                    if (other) other.click();
                }""",
                module_label,
            )
            page.wait_for_timeout(900)

        # The Setup links are usually already in the top document, so try the
        # target directly first. Clicking the module label when its menu is
        # already open would toggle it shut, which is what made this flaky.
        # Only fall back to opening the menu if the direct click didn't land.
        attempts = 3
        for attempt in range(attempts):
            if click_target():
                try:
                    heading.wait_for(timeout=timeout if attempt == attempts - 1 else 8_000)
                    return
                except Exception:
                    pass
            open_module_menu()
            if attempt == 0:
                # A second click switches modules when a different one was active.
                open_module_menu()

        click_target()
        heading.wait_for(timeout=timeout)

    def reset_ui(self):
        """
        Return the page to a clean, clickable state.

        Long runs share one browser session, so leftovers accumulate: an open
        dialog or dropdown from a previous scenario, or the Pendo guide overlay,
        will silently swallow clicks and surface later as an unrelated timeout.
        Called between scenarios so each one starts from the same state.
        """
        try:
            self.page.evaluate(
                """() => {
                    document.querySelectorAll(
                        '[id^="pendo-"], ._pendo-backdrop, .nav-popup-overlay'
                    ).forEach(e => e.remove());
                    const d = document.querySelector('iframe#iamain');
                    if (d && d.contentDocument) {
                        d.contentDocument.querySelectorAll(
                            '[id^="pendo-"], ._pendo-backdrop, .nav-popup-overlay'
                        ).forEach(e => e.remove());
                    }
                }"""
            )
        except Exception:
            pass
        # Escape twice: one for an open dropdown, one for a dialog behind it.
        for _ in range(2):
            try:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(150)
            except Exception:
                break

    # ── Header actions (direct control, else "More actions" overflow) ──────────

    def _open_header_more_actions(self):
        """
        Open the header's overflow ("More actions") popover.

        View/Edit pages can render TWO controls with aria-label="More actions"
        (header trigger + nested three-dot). Before the popover is open only the
        header trigger is visible, so the ``:visible`` filter targets it
        deterministically.
        """
        self.frame.locator('[aria-label="More actions"]:visible').first.click()
        self.page.wait_for_timeout(500)

    def _action_locator(self, name: str) -> Locator:
        """
        Role-agnostic locator for a *visible* header action. The ``:visible``
        filter is essential: several actions (notably "Delete") are pre-rendered
        hidden in the DOM inside the confirmation dialog, and must never be
        clicked in place of the live menu item.
        """
        return self.frame.locator(
            f'[aria-label="{name}"]:visible, '
            f'[role="menuitem"]:has-text("{name}"):visible, '
            f'button:has-text("{name}"):visible'
        )

    def click_header_action(self, name: str, direct_timeout: int = 2_000):
        """Click a header action, falling back to the overflow menu if it collapsed."""
        direct = self._action_locator(name)
        try:
            direct.first.wait_for(state="visible", timeout=direct_timeout)
            direct.first.click()
            return
        except Exception:
            pass
        self._open_header_more_actions()
        self._action_locator(name).first.click()

    # ── Delete confirmation modal ──────────────────────────────────────────────

    def delete_dialog(self, match_text: str = DELETE_DIALOG_TEXT) -> Locator:
        """
        The delete confirmation modal.

        Located by text content rather than visibility because the
        [role="dialog"] wrapper has a zero-size bounding box. ``.last`` guards
        against stale, unmounted instances left by earlier tests on a
        session-scoped page.
        """
        return self.frame.locator('[role="dialog"]').filter(has_text=match_text).last

    def get_delete_modal_title(self, match_text: str = DELETE_DIALOG_TEXT) -> str:
        return self.delete_dialog(match_text).get_by_role("heading").first.inner_text()

    def get_delete_modal_message(self, match_text: str = DELETE_DIALOG_TEXT) -> str:
        return self.delete_dialog(match_text).inner_text()

    def confirm_delete(self, match_text: str = DELETE_DIALOG_TEXT):
        self.delete_dialog(match_text).get_by_role("button", name="Delete").first.click()

    def cancel_delete(self, match_text: str = DELETE_DIALOG_TEXT):
        self.delete_dialog(match_text).get_by_role("button", name="Cancel").first.click()

    # ── Search-as-you-type picker ──────────────────────────────────────────────

    def fill_picker(
        self,
        field_name: str,
        query: str,
        option_text: Optional[str] = None,
        wait_timeout: int = 8_000,
    ):
        """
        Fill a search-as-you-type combobox and pick the matching option.

        The dropdown is populated by a server round-trip after typing, so we wait
        for the target option to actually *appear* rather than sleeping a fixed
        interval — under automated/headless conditions this can take noticeably
        longer than it appears to when driving the app by hand.
        """
        combo = self.frame.get_by_role("combobox", name=field_name).first
        combo.click()
        combo.fill(query)
        target = option_text or query
        option = self.frame.get_by_role("option", name=target, exact=False)
        try:
            option.first.wait_for(state="visible", timeout=wait_timeout)
            option.first.click()
        except Exception:
            pass  # no matching option rendered — leave the field as typed

    # ── Toast / notification ────────────────────────────────────────────────────

    def get_toast_message(self) -> str:
        """Returns the text of the first visible toast / alert notification."""
        return self.frame.locator('[role="alert"], .toast, .notification').first.inner_text()

    # ── Heading / title ─────────────────────────────────────────────────────────

    def get_page_heading(self) -> str:
        return self.frame.locator("h1").inner_text()

    def wait_for_heading(self, text: str, timeout: int = 10_000):
        self.frame.locator("h1", has_text=text).wait_for(timeout=timeout)
