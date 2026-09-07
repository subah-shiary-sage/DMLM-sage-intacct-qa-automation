"""
fee_type_page.py
Page Object for the Loan fee type Create / View / Edit / Delete pages.

Selectors captured against the live app 2026-08-12
(release www-p303 / SNL_release_monthly / LME entity):

  * Create page : H1 "Create loan fee type". Fields — Name (mandatory), GL
                  account (mandatory combobox), Item (optional combobox),
                  Description (optional). Save is a split control; Cancel is
                  rendered but can collapse into the header overflow at narrow
                  widths. No Status field on Create.
  * View page   : H1 "Loan fee type: <ID>" — the internal record ID, not the
                  name. Edit / Delete in the header, plus a 3-dot More actions.
  * Edit page   : H1 "Edit loan-management/loan-fee-type: <ID>--<Name>" — the
                  raw internal object path. Status becomes an editable combobox.
  * Delete modal: "Delete loan fee type" with the record name in the body.

  KNOWN DEFECT baked into the selectors: the Name input's aria-label is
  "Loan type", not "Name" (Bug #29), and it carries no maxlength (Bug #87).
  NAME_INPUT deliberately targets the real, defective label so the POM works
  today; SL 8 asserts the label is wrong rather than assuming it is right.
"""

from typing import Optional

from ..base_page import BasePage


class LoanFeeTypePage(BasePage):

    # The Name field is mislabelled "Loan type" in the DOM — see Bug #29.
    NAME_INPUT = 'input[aria-label="Loan type"]'
    NAME_ARIA_LABEL = "Loan type"
    DESCRIPTION_INPUT = 'input[aria-label="Description"]'

    SECTION_HEADER = "Loan fee type information"
    DELETE_DIALOG = "Delete loan fee type"

    # ── Headings ───────────────────────────────────────────────────────────────

    def get_page_title(self) -> str:
        return self.frame.locator("h1").first.inner_text().strip()

    def wait_for_create_page(self, timeout: int = 15_000):
        self.frame.get_by_role("heading", name="Create loan fee type").wait_for(timeout=timeout)

    def wait_for_view_page(self, timeout: int = 15_000):
        self.frame.locator("h1").filter(has_text="Loan fee type:").filter(
            has_not_text="Edit"
        ).filter(has_not_text="Create").first.wait_for(timeout=timeout)
        self.wait_for_view_hydrated()

    def wait_for_view_hydrated(self, timeout: int = 10_000):
        """
        Wait until the view page has real values.

        The page paints "--" placeholders first and fills them in a moment later,
        so reading immediately after the heading appears yields "--" for every
        field and looks exactly like data that failed to save.
        """
        deadline = timeout
        while deadline > 0:
            if (self.view_field_text("GL account") or "--") != "--":
                return
            self.page.wait_for_timeout(400)
            deadline -= 400

    def wait_for_edit_page(self, timeout: int = 15_000):
        self.frame.locator("h1").filter(has_text="Edit").filter(
            has_text="loan-fee-type"
        ).first.wait_for(timeout=timeout)

    # ── Form fields ────────────────────────────────────────────────────────────

    def fill_name(self, name: str):
        inp = self.frame.locator(self.NAME_INPUT).first
        inp.fill(name)
        inp.evaluate("el => el.blur()")

    def get_name_value(self) -> str:
        return self.frame.locator(self.NAME_INPUT).first.input_value()

    def get_name_maxlength(self) -> Optional[str]:
        """None means the input imposes no client-side length cap (Bug #87)."""
        return self.frame.locator(self.NAME_INPUT).first.get_attribute("maxlength")

    def fill_description(self, text: str):
        self.frame.locator(self.DESCRIPTION_INPUT).first.fill(text)

    def get_description_value(self) -> str:
        return self.frame.locator(self.DESCRIPTION_INPUT).first.input_value()

    def get_description_maxlength(self) -> Optional[str]:
        """None means no client-side cap — the 500 limit is server-side only."""
        return self.frame.locator(self.DESCRIPTION_INPUT).first.get_attribute("maxlength")

    def set_gl_account(self, query: str, option_text: Optional[str] = None):
        self.fill_picker("GL account", query, option_text)

    def get_gl_account_value(self) -> str:
        return self.frame.get_by_role("combobox", name="GL account").first.input_value()

    def set_item(self, query: str, option_text: Optional[str] = None):
        self.fill_picker("Item", query, option_text)

    def get_item_value(self) -> str:
        return self.frame.get_by_role("combobox", name="Item").first.input_value()

    def set_status(self, status: str):
        """Status combobox — Edit page only ('Active' / 'Inactive')."""
        combo = self.frame.get_by_role("combobox", name="Status").first
        combo.click()
        option = self.frame.get_by_role("option", name=status, exact=True)
        option.first.wait_for(state="visible", timeout=5_000)
        option.first.click()

    def has_status_field(self) -> bool:
        return self.frame.get_by_role("combobox", name="Status").count() > 0

    # ── Field metadata (presence / mandatory markers) ──────────────────────────

    def field_labels(self) -> list[str]:
        """Visible field labels on the form, with the mandatory '*' stripped."""
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                return [...d.querySelectorAll('label')]
                    .map(e => e.textContent.replace(/\\u00a0/g, ' ').trim())
                    .filter(t => t && t !== '*' && t.length < 60);
            }"""
        )

    def is_field_mandatory(self, label: str) -> bool:
        """True when the field's label carries the red mandatory asterisk."""
        return self.page.evaluate(
            """(label) => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const norm = s => s.replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
                return [...d.querySelectorAll('label')]
                    .some(e => norm(e.textContent).replace(/\\s*\\*$/, '') === label
                            && norm(e.textContent).endsWith('*'));
            }""",
            label,
        )

    def has_field(self, label: str) -> bool:
        norm = [l.rstrip(" *").strip() for l in self.field_labels()]
        return label in norm

    # ── Save / Cancel ──────────────────────────────────────────────────────────

    def save(self):
        self.click_header_action("Save")

    def cancel(self):
        self.click_header_action("Cancel")

    def save_menu_options(self) -> list[str]:
        """
        Labels in the Save split-button dropdown.

        Save is a split control: the caret next to it opens Save / Save and
        close / Save and new. At narrow widths the whole thing collapses into
        the header overflow, so fall back to that.
        """
        caret = self.frame.locator(
            '[aria-label="Save"] ~ button, [aria-label="More actions"]:visible'
        )
        if caret.count():
            caret.first.click()
            self.page.wait_for_timeout(600)
        items = self.frame.locator('[role="menuitem"], [role="dialog"] button')
        return [
            t
            for t in ((items.nth(i).inner_text() or "").strip() for i in range(items.count()))
            if t
        ]

    def save_via(self, option: str):
        """Save using a named variant: 'Save', 'Save and close', 'Save and new'."""
        if option == "Save":
            self.save()
            return
        self.click_header_action("Save")
        self.page.wait_for_timeout(400)
        target = self.frame.get_by_role("button", name=option).or_(
            self.frame.locator(f'[role="menuitem"]:has-text("{option}")')
        )
        target.first.click()

    def has_back_arrow(self) -> bool:
        return self.frame.get_by_role("button", name="Back to previous page").count() > 0

    # ── View page ──────────────────────────────────────────────────────────────

    def click_edit(self):
        self.click_header_action("Edit")
        self.wait_for_edit_page()

    def click_delete(self):
        self.click_header_action("Delete")
        self.frame.get_by_role("heading", name=self.DELETE_DIALOG).last.wait_for(timeout=10_000)

    def click_breadcrumb_to_list(self):
        self.frame.get_by_role("link", name="Loan fee types").first.click()
        self.frame.get_by_role("heading", name="Loan fee types").wait_for(timeout=15_000)

    def has_breadcrumb(self) -> bool:
        return self.frame.get_by_role("link", name="Loan fee types").count() > 0

    def view_field_text(self, label: str) -> str:
        """Read a value from the read-only View page by its label."""
        return self.page.evaluate(
            """(label) => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const norm = s => (s || '').replace(/\\u00a0/g, ' ').trim();
                const el = [...d.querySelectorAll('*')]
                    .find(e => e.children.length === 0 && norm(e.textContent) === label);
                if (!el) return '';
                let n = el.parentElement;
                for (let i = 0; i < 3 && n; i++, n = n.parentElement) {
                    const t = norm(n.textContent).replace(label, '').trim();
                    if (t) return t;
                }
                return '';
            }""",
            label,
        )

    def is_view_read_only(self) -> bool:
        """True when the View page renders no editable inputs/comboboxes."""
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                return d.querySelectorAll(
                    'input:not([type=hidden]):not([disabled]):not([readonly]), [role=combobox]'
                ).length === 0;
            }"""
        )

    def open_three_dot_menu(self):
        """
        Open the record's own "More actions" (3-dot) menu on the View page.

        Edit and Delete render as their own buttons here, so the visible
        More-actions control is the record menu. Its contents render into a
        popover that is only present once opened.
        """
        self.frame.locator(
            '[aria-label="More actions"]:visible, button[aria-haspopup]:visible'
        ).last.click()
        self.page.wait_for_timeout(900)

    def three_dot_menu_items(self) -> list[str]:
        """Labels in the currently-open More actions popover."""
        return [
            t
            for t in self.page.evaluate(
                """() => {
                    const d = document.querySelector('iframe#iamain').contentDocument;
                    const nodes = d.querySelectorAll(
                        '[role=menuitem], [role=menu] a, [role=menu] button,'
                        + ' [role=dialog] a, [role=dialog] button, ul[class*=menu] li'
                    );
                    return [...nodes].map(e => (e.textContent || '').trim());
                }"""
            )
            if t
        ]

    # ── Validation ─────────────────────────────────────────────────────────────

    def error_banner_text(self) -> str:
        banner = self.frame.get_by_role("alert")
        return banner.first.inner_text().strip() if banner.count() else ""

    def has_inline_field_error(self) -> bool:
        return self.frame.locator('[aria-invalid="true"]').count() > 0

    def toast_text(self) -> str:
        el = self.frame.locator('[role="alert"], [role="status"]')
        return el.first.inner_text().strip() if el.count() else ""

    # ── Toast capture ──────────────────────────────────────────────────────────
    #
    # Success toasts ("Loan fee type created") are short-lived — reading after the
    # action has already navigated usually returns nothing, which looks exactly
    # like the app showing no confirmation at all. Arm the recorder *before* the
    # action, then read what it caught.

    def start_recording_toasts(self):
        """Record every alert/status node added from now on."""
        self.page.evaluate(
            """() => {
                window.__toasts = [];
                const grab = (n) => {
                    if (!n || !n.querySelectorAll) return;
                    for (const e of [n, ...n.querySelectorAll('*')]) {
                        const r = e.getAttribute && e.getAttribute('role');
                        if (r === 'alert' || r === 'status') {
                            const t = (e.textContent || '').trim();
                            if (t) window.__toasts.push(t);
                        }
                    }
                };
                const d = document.querySelector('iframe#iamain').contentDocument;
                if (window.__toastObserver) window.__toastObserver.disconnect();
                window.__toastObserver = new MutationObserver(
                    (ms) => ms.forEach((m) => m.addedNodes.forEach(grab))
                );
                window.__toastObserver.observe(d.body, {childList: true, subtree: true});
            }"""
        )

    def recorded_toasts(self) -> list[str]:
        """Everything the recorder caught since start_recording_toasts()."""
        try:
            return self.page.evaluate("() => window.__toasts || []")
        except Exception:
            return []

    def wait_for_toast(self, timeout: int = 6_000) -> str:
        """
        First recorded toast, waiting up to `timeout` for one to appear.

        Returns "" if none was ever shown — which is a real finding, not a
        capture artifact, because the recorder was armed beforehand.
        """
        remaining = timeout
        while remaining > 0:
            hits = self.recorded_toasts()
            if hits:
                return hits[0]
            self.page.wait_for_timeout(300)
            remaining -= 300
        live = self.toast_text()
        return live or ""

    # ── a11y probes (SL 47) ────────────────────────────────────────────────────

    def untranslated_aria_keys(self) -> list[str]:
        """
        Raw resource keys leaking into the UI as aria-labels or text
        (IA.*, BULK_SELECTED) — the Bug #43 / IAUI-616 family.
        """
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const hits = new Set();
                const bad = /^(IA\\.[A-Z0-9_.]+|BULK_SELECTED)$/;
                const all = d.querySelectorAll('[aria-label], [title], [alt]');
                for (const e of all) {
                    for (const a of ['aria-label', 'title', 'alt']) {
                        const v = (e.getAttribute(a) || '').trim();
                        if (bad.test(v)) hits.add(v);
                    }
                }
                for (const e of d.querySelectorAll('th, [role=columnheader], span, div')) {
                    if (e.children.length === 0) {
                        const t = (e.textContent || '').trim();
                        if (bad.test(t)) hits.add(t);
                    }
                }
                return [...hits];
            }"""
        )
