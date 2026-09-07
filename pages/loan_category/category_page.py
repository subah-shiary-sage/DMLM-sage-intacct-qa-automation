"""
category_page.py
Page Object for the Loan account category Create / View / Edit / Delete pages
(Lending Management → Setup → Loan account categories).

NOTE: a different object from ``pages/depository_category`` (Depository
Management). This one backs the "Loan Category - CRUD" checklist.

Selectors captured against the live app 2026-08-17
(release www-p303 / SNL_release_monthly / LME entity):

  * Create page : H1 "Create loan account category". Fields — Name (mandatory,
                  correctly labelled "Name"), Document sequence (optional
                  combobox/picker), Description (optional). No Status on create.
  * View page   : H1 "Loan account categories: <ID>" — the *plural* noun plus
                  the internal record ID rather than the record's name; the
                  checklist expects "Loan account category: <Name>" (SL 30).
  * Edit page   : H1 contains "Edit" and the object path.
  * Delete modal: titled "Delete loan category" (singular, and *not* matching
                  the "loan account category" wording used everywhere else on
                  the page), body "The following loan account category will be
                  permanently deleted:" plus the record name. Delete + Cancel;
                  no Close (X).

No field carries a maxlength attribute, so the documented 200 (Name) and
500/1000 (Description) limits are enforced server-side only.
"""

from typing import Optional

from ..base_page import BasePage


class LoanCategoryPage(BasePage):

    NAME_INPUT = 'input[aria-label="Name"]'
    NAME_ARIA_LABEL = "Name"
    DOC_SEQ_INPUT = 'input[aria-label="Document sequence"]'
    DOC_SEQ_LABEL = "Document sequence"
    DESCRIPTION_INPUT = 'input[aria-label="Description"]'

    CREATE_HEADING = "Create loan account category"
    VIEW_HEADING_PREFIX = "Loan account categories:"
    # The modal title says "loan category", not "loan account category".
    DELETE_DIALOG = "Delete loan category"

    # ── Headings ───────────────────────────────────────────────────────────────

    def get_page_title(self) -> str:
        return self.frame.locator("h1").first.inner_text().strip()

    def wait_for_create_page(self, timeout: int = 15_000):
        self.frame.get_by_role("heading", name=self.CREATE_HEADING).wait_for(timeout=timeout)

    def wait_for_view_page(self, timeout: int = 15_000):
        self.frame.locator("h1").filter(has_text=self.VIEW_HEADING_PREFIX).filter(
            has_not_text="Edit"
        ).filter(has_not_text="Create").first.wait_for(timeout=timeout)
        self.wait_for_view_hydrated()

    def wait_for_view_hydrated(self, timeout: int = 10_000):
        """
        Wait until the view page shows real values.

        Like the other LME detail pages it paints "--" placeholders first, so an
        immediate read looks exactly like data that failed to save.
        """
        deadline = timeout
        while deadline > 0:
            if (self.view_field_text(self.NAME_ARIA_LABEL) or "--") != "--":
                return
            self.page.wait_for_timeout(400)
            deadline -= 400

    def wait_for_edit_page(self, timeout: int = 15_000):
        self.frame.locator("h1").filter(has_text="Edit").first.wait_for(timeout=timeout)

    # ── Form fields ────────────────────────────────────────────────────────────

    def fill_name(self, name: str):
        inp = self.frame.locator(self.NAME_INPUT).first
        inp.fill(name)
        inp.evaluate("el => el.blur()")

    def get_name_value(self) -> str:
        return self.frame.locator(self.NAME_INPUT).first.input_value()

    def get_name_maxlength(self) -> Optional[str]:
        """None means no client-side cap — the 200 limit is server-side only."""
        return self.frame.locator(self.NAME_INPUT).first.get_attribute("maxlength")

    def fill_description(self, text: str):
        self.frame.locator(self.DESCRIPTION_INPUT).first.fill(text)

    def get_description_value(self) -> str:
        return self.frame.locator(self.DESCRIPTION_INPUT).first.input_value()

    def get_description_maxlength(self) -> Optional[str]:
        return self.frame.locator(self.DESCRIPTION_INPUT).first.get_attribute("maxlength")

    def fill_document_sequence(self, value: str, option_text: Optional[str] = None):
        """Document sequence is a search-as-you-type picker, not a plain text box."""
        self.fill_picker(self.DOC_SEQ_LABEL, value, option_text)

    def type_document_sequence(self, value: str):
        """Type a raw value without picking an option (for invalid-value checks)."""
        inp = self.frame.locator(self.DOC_SEQ_INPUT).first
        inp.fill(value)
        inp.evaluate("el => el.blur()")

    def get_document_sequence_value(self) -> str:
        return self.frame.locator(self.DOC_SEQ_INPUT).first.input_value()

    def document_sequence_options(self, query: str = "") -> list[str]:
        """Open the Document sequence picker and list what it offers."""
        combo = self.frame.get_by_role("combobox", name=self.DOC_SEQ_LABEL).first
        combo.click()
        if query:
            combo.fill(query)
        self.page.wait_for_timeout(1_200)
        opts = self.frame.get_by_role("option")
        return [
            t
            for t in ((opts.nth(i).inner_text() or "").strip() for i in range(opts.count()))
            if t
        ]

    def set_status(self, status: str):
        """Status combobox — Edit page only ('Active' / 'Inactive')."""
        combo = self.frame.get_by_role("combobox", name="Status").first
        combo.click()
        option = self.frame.get_by_role("option", name=status, exact=True)
        option.first.wait_for(state="visible", timeout=5_000)
        option.first.click()

    def has_status_field(self) -> bool:
        return self.frame.get_by_role("combobox", name="Status").count() > 0

    # ── Field metadata ─────────────────────────────────────────────────────────

    def field_labels(self) -> list[str]:
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                return [...d.querySelectorAll('label')]
                    .map(e => e.textContent.replace(/\\u00a0/g, ' ').trim())
                    .filter(t => t && t !== '*' && t.length < 60);
            }"""
        )

    def is_field_mandatory(self, label: str) -> bool:
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
        return label in [l.rstrip(" *").strip() for l in self.field_labels()]

    def editable_field_labels(self) -> list[str]:
        """Labels whose control is currently editable — for field-lock checks."""
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const live = [...d.querySelectorAll(
                    'input:not([type=hidden]):not([disabled]):not([readonly]), [role=combobox]'
                )];
                return live.map(e => e.getAttribute('aria-label')).filter(Boolean);
            }"""
        )

    # ── Save / Cancel ──────────────────────────────────────────────────────────

    def save(self):
        self.click_header_action("Save")

    def cancel(self):
        self.click_header_action("Cancel")

    def save_menu_options(self) -> list[str]:
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
        """'Save', 'Save and close', or 'Save and new'."""
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

    def has_breadcrumb(self) -> bool:
        return self.frame.get_by_role("link", name="Loan account categories").count() > 0

    def click_breadcrumb_to_list(self):
        self.frame.get_by_role("link", name="Loan account categories").first.click()
        self.frame.get_by_role("heading", name="Loan account categories").wait_for(
            timeout=15_000
        )

    def view_field_text(self, label: str) -> str:
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
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                return d.querySelectorAll(
                    'input:not([type=hidden]):not([disabled]):not([readonly]), [role=combobox]'
                ).length === 0;
            }"""
        )

    def open_three_dot_menu(self):
        self.frame.locator(
            '[aria-label="More actions"]:visible, button[aria-haspopup]:visible'
        ).last.click()
        self.page.wait_for_timeout(900)

    def three_dot_menu_items(self) -> list[str]:
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

    # ── Validation / messages ──────────────────────────────────────────────────

    def error_banner_text(self) -> str:
        banner = self.frame.get_by_role("alert")
        return banner.first.inner_text().strip() if banner.count() else ""

    def has_inline_field_error(self) -> bool:
        return self.frame.locator('[aria-invalid="true"]').count() > 0

    def toast_text(self) -> str:
        el = self.frame.locator('[role="alert"], [role="status"]')
        return el.first.inner_text().strip() if el.count() else ""

    def start_recording_toasts(self):
        """
        Record alert/status nodes from now on.

        Success toasts are short-lived; reading after the post-save redirect
        usually returns nothing, which looks like no confirmation at all.
        """
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
        try:
            return self.page.evaluate("() => window.__toasts || []")
        except Exception:
            return []

    def wait_for_toast(self, timeout: int = 6_000) -> str:
        remaining = timeout
        while remaining > 0:
            hits = self.recorded_toasts()
            if hits:
                return hits[0]
            self.page.wait_for_timeout(300)
            remaining -= 300
        return self.toast_text() or ""

    def untranslated_aria_keys(self) -> list[str]:
        """Raw resource keys (IA.*, BULK_SELECTED) leaking into the UI."""
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const hits = new Set();
                const bad = /^(IA\\.[A-Z0-9_.]+|BULK_SELECTED)$/;
                for (const e of d.querySelectorAll('[aria-label], [title], [alt]')) {
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
