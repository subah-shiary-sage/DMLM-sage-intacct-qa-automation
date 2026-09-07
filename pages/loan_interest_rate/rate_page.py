"""
rate_page.py
Page Object for the Loan Interest Rate Create / View / Edit / Delete pages
(Lending Management → Setup → Loan interest rates).

Selectors verified against live DOM 2026-07-16 (DMLM entity).

Key behaviours discovered live:
  * Create page  : Save is role="menuitem"; Cancel is a visible button.
                   Fields: Name (required), Type (required radio:
                   Revolving/Non-revolving). No separate "Loan type" picker —
                   the list's "Loan type" column is just the Type value.
                   Loan interest rate schedule grid: Start date (required,
                   free-typed MM/DD/YYYY), Interest rate (%) (required),
                   Notes, Attachment (optional). TWO server-side validations
                   undocumented anywhere in the UI: at least one schedule row
                   is required, AND Start date must be the first day of a
                   month (any other day is rejected).
  * View page    : H1 is "Loan interest rates: <ID>" — PLURAL "rates"
                   (matches the module name), unlike Loan Type's singular
                   "Loan type: <ID>". No name in the heading. Edit / Delete
                   directly visible in the header (not nested). Status IS
                   shown here (defaults to Active, absent from Create).
  * Edit page    : H1 is "Edit loan interest rate: <ID>--<Name>" on the
                   current release. Older builds exposed the internal object
                   path instead, so the wait helper uses the stable "Edit"
                   prefix.
                   Type renders as read-only plain text (cannot be changed).
                   Status is an editable combobox. Save/Cancel are collapsed
                   into the header "More actions" overflow.
  * Delete modal : dialog "Delete loan interest rate" with Delete / Cancel.
                   Same framework component as Depository Account Category's/
                   Loan Type's delete modal — the [role="dialog"] wrapper
                   itself is an unreliable Playwright-visibility target
                   (zero-bbox quirk), so assertions and waits target the
                   heading / buttons instead.
"""

import time
from typing import Optional
from ..base_page import BasePage


class LoanInterestRatePage(BasePage):

    # ── Field selectors ────────────────────────────────────────────────────────
    NAME_INPUT = 'input[aria-label="Name"]'

    # ── Collapsible section ────────────────────────────────────────────────────
    SECTION_HEADER = "Loan interest rate information"

    # ── Delete confirmation modal ──────────────────────────────────────────────
    DELETE_DIALOG = "Delete loan interest rate"

    # ── Validation errors (inline + toast) ─────────────────────────────────────
    VALIDATION_ERROR = '[aria-invalid="true"], [class*="error"], [role="alert"]'

    # ══════════════════════════════════════════════════════════════════════════
    # Page heading helpers
    # ══════════════════════════════════════════════════════════════════════════

    def get_page_title(self) -> str:
        return self.frame.locator("h1").first.inner_text()

    def wait_for_view_page(self, timeout: int = 15_000):
        """Wait for the read-only View page heading 'Loan interest rates: <ID>'."""
        self.frame.locator("h1").filter(
            has_text="Loan interest rates:"
        ).filter(has_not_text="Edit").filter(has_not_text="Create").first.wait_for(timeout=timeout)
        # The heading/field values hydrate asynchronously a moment after the
        # shell renders — give the page a beat to settle before returning
        # control to the caller (mirrors wait_for_edit_page's hydration wait).
        self.page.wait_for_timeout(500)

    def wait_for_edit_page(self, timeout: int = 10_000):
        # The title text differs across release builds (some expose the
        # internal object path, others use a friendly label), so wait on the
        # stable Edit prefix only.
        self.frame.locator("h1").filter(has_text="Edit").first.wait_for(timeout=timeout)
        # Live-DOM discovery: the Edit page's initial paint shows "--"
        # placeholders and an empty Name field; real data (Name, Type,
        # Status, schedule rows) hydrates asynchronously a moment later.
        # Poll the Name field until it actually has a value before returning.
        name_input = self.frame.locator(self.NAME_INPUT).first
        name_input.wait_for(state="visible", timeout=timeout)
        deadline = time.monotonic() + (timeout / 1000)
        while time.monotonic() < deadline:
            if name_input.input_value().strip():
                return
            self.page.wait_for_timeout(200)

    # ══════════════════════════════════════════════════════════════════════════
    # Form interactions (Create & Edit)
    # ══════════════════════════════════════════════════════════════════════════

    def fill_name(self, name: str):
        inp = self.frame.locator(self.NAME_INPUT).first
        inp.fill(name)
        inp.evaluate("el => el.blur()")

    def get_name_value(self) -> str:
        return self.frame.locator(self.NAME_INPUT).first.input_value()

    def is_name_editable(self) -> bool:
        field = self.frame.locator(self.NAME_INPUT).first
        return field.count() > 0 and field.is_editable()

    def select_type(self, type_label: str):
        """Type radio button — 'Revolving' or 'Non-revolving'. Create page only
        (read-only on Edit)."""
        self.frame.get_by_role("radio", name=type_label, exact=True).click()

    def set_status(self, status: str):
        """Status combobox — Edit page only ('Active' / 'Inactive')."""
        combo = self.frame.get_by_role("combobox", name="Status").first
        combo.click()
        option = self.frame.get_by_role("option", name=status, exact=True)
        try:
            option.first.wait_for(state="visible", timeout=5_000)
            option.first.click()
        except Exception:
            self.frame.get_by_text(status, exact=True).first.click()

    def get_status_value(self) -> str:
        combo = self.frame.get_by_role("combobox", name="Status").first
        return combo.input_value() if combo.count() else ""

    # ══════════════════════════════════════════════════════════════════════════
    # Loan interest rate schedule grid
    # ══════════════════════════════════════════════════════════════════════════

    def _schedule_grid(self):
        return self.frame.get_by_role("grid").first

    def _schedule_rows(self):
        """Return grid rows including the header at index zero."""
        return self._schedule_grid().get_by_role("row")

    def _activate_schedule_row(self, row_index: int, column_index: int = 1):
        """Activate a virtualised grid row so its editors are rendered.

        FlexGrid only renders ``input`` controls for the active row. Clicking
        the row wrapper does not work because that wrapper has a zero-sized
        box; a visible grid cell must be clicked instead.
        """
        rows = self._schedule_rows()
        row = rows.nth(row_index + 1)
        cell = row.get_by_role("gridcell").nth(column_index)
        cell.click()
        self.page.wait_for_timeout(200)
        return self._schedule_rows().nth(row_index + 1)

    def get_schedule_row_count(self) -> int:
        return self._schedule_grid().locator("tbody tr, [role='row']").count() - 1  # minus header

    def click_add_row(self):
        """Adds a new row — inserted at the TOP of the grid (existing rows shift down)."""
        self.frame.get_by_role("button", name="Add row").first.click()
        self.page.wait_for_timeout(400)

    def click_remove_row(self, row_index: int = 0):
        rows = self._schedule_rows()
        rows.nth(row_index + 1).get_by_role("button", name="Remove row").click()
        self.page.wait_for_timeout(400)

    def add_row_is_enabled(self) -> bool:
        button = self.frame.get_by_role("button", name="Add row").first
        return button.count() > 0 and button.is_enabled()

    def row_remove_is_enabled(self, row_index: int = 0) -> bool:
        button = self._schedule_rows().nth(row_index + 1).get_by_role(
            "button", name="Remove row"
        )
        return button.count() > 0 and button.first.is_enabled()

    def set_row_start_date(self, value: str, row_index: int = 0):
        """`value` as MM/DD/YYYY — free-typed, no calendar popup required.
        Must be the first day of a month or save is rejected server-side."""
        row = self._activate_schedule_row(row_index, column_index=1)
        combo = row.get_by_role("combobox").first
        combo.click()
        combo.fill(value)
        self.page.keyboard.press("Tab")

    def set_row_interest_rate(self, value: str, row_index: int = 0):
        row = self._activate_schedule_row(row_index, column_index=2)
        row.get_by_role("textbox").first.fill(value)

    def set_row_notes(self, value: str, row_index: int = 0):
        row = self._activate_schedule_row(row_index, column_index=3)
        row.get_by_role("textbox").nth(1).fill(value)

    def get_row_start_date(self, row_index: int = 0) -> str:
        row = self._activate_schedule_row(row_index, column_index=1)
        return row.get_by_role("combobox").first.input_value()

    def get_row_interest_rate(self, row_index: int = 0) -> str:
        row = self._activate_schedule_row(row_index, column_index=2)
        return row.get_by_role("textbox").first.input_value()

    def get_row_notes(self, row_index: int = 0) -> str:
        row = self._activate_schedule_row(row_index, column_index=3)
        return row.get_by_role("textbox").nth(1).input_value()

    def schedule_field_is_editable(self, row_index: int, field: str) -> bool:
        """Return whether a schedule field is editable after row activation."""
        columns = {"start_date": 1, "interest_rate": 2, "notes": 3}
        if field not in columns:
            raise ValueError(f"Unknown schedule field: {field}")
        row = self._activate_schedule_row(row_index, columns[field])
        if field == "start_date":
            control = row.get_by_role("combobox").first
        elif field == "interest_rate":
            control = row.get_by_role("textbox").first
        else:
            control = row.get_by_role("textbox").nth(1)
        return control.count() > 0 and control.is_editable()

    def attachment_is_editable(self, row_index: int = 0) -> bool:
        control = self.attachment_control(row_index)
        return control.count() > 0 and control.is_editable()

    def attachment_control(self, row_index: int = 0):
        row = self._activate_schedule_row(row_index, column_index=4)
        return row.locator('input[aria-label^="attachment.key-"]').first

    def status_is_editable(self) -> bool:
        control = self.frame.get_by_role("combobox", name="Status").first
        return control.count() > 0 and control.is_editable()

    # ══════════════════════════════════════════════════════════════════════════
    # Save / Cancel  (robust across Create menuitem vs Edit overflow)
    # ══════════════════════════════════════════════════════════════════════════

    def save(self):
        self.click_header_action("Save")

    def cancel(self):
        self.click_header_action("Cancel")

    def header_action_is_available(self, name: str) -> bool:
        action = self._action_locator(name)
        if action.count() and action.first.is_visible():
            return True
        try:
            self._open_header_more_actions()
        except Exception:
            return False
        action = self._action_locator(name)
        return action.count() > 0 and action.first.is_visible()

    # ══════════════════════════════════════════════════════════════════════════
    # View page actions
    # ══════════════════════════════════════════════════════════════════════════

    def click_edit(self):
        button = self.frame.get_by_role("button", name="Edit", exact=True)
        button.last.wait_for(state="visible", timeout=10_000)
        self.page.wait_for_timeout(800)
        button.last.click()
        self.wait_for_edit_page(timeout=15_000)

    def click_delete(self):
        self.click_header_action("Delete")
        # Wait on the heading, not the dialog role element — the dialog's own
        # [role="dialog"] wrapper has a zero-size bounding box (framework
        # quirk shared with Depository Account Category's/Loan Type's delete
        # modal). `.last` because the session-scoped page can accumulate
        # stale, unmounted confirm-dialog instances from earlier tests.
        self.frame.get_by_role("heading", name=self.DELETE_DIALOG).last.wait_for(timeout=10_000)

    def click_back_to_list(self):
        link = self.frame.get_by_role("link", name="Loan interest rates")
        if link.count() > 0 and link.first.is_visible():
            link.first.click()
        else:
            self.frame.get_by_role(
                "button", name="Back to previous page"
            ).first.click()
        self.frame.get_by_role(
            "heading", name="Loan interest rates"
        ).wait_for(timeout=10_000)

    def is_name_readonly(self) -> bool:
        return self.frame.locator(self.NAME_INPUT).count() == 0

    def get_field_text(self, field_label: str) -> str:
        return self.frame.get_by_label(field_label).first.inner_text()

    def view_has_editable_form_controls(self) -> bool:
        """Ignore header actions and report only editable record/grid fields."""
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                return [...d.querySelectorAll('input, textarea, select')]
                    .some(e => !e.disabled && !e.readOnly && e.offsetParent !== null);
            }"""
        )

    # ══════════════════════════════════════════════════════════════════════════
    # View page three-dot menu
    # ══════════════════════════════════════════════════════════════════════════

    def open_view_three_dot_menu(self):
        self._open_header_more_actions()
        triggers = self.frame.locator('[aria-label="More actions"]:visible')
        if triggers.count():
            triggers.last.click()
        self.page.wait_for_timeout(400)

    def view_three_dot_menu_items(self) -> list[str]:
        self.open_view_three_dot_menu()
        controls = self.frame.locator(
            '[role="menuitem"]:visible, [role="dialog"] button:visible'
        )
        return [
            text
            for text in (
                (controls.nth(index).inner_text() or "").strip()
                for index in range(controls.count())
            )
            if text
        ]

    # ══════════════════════════════════════════════════════════════════════════
    # Collapsible sections
    # ══════════════════════════════════════════════════════════════════════════

    def _get_named_section_toggle(self, section_label: str):
        heading = self.frame.get_by_text(section_label, exact=True).first
        return heading.locator(
            "xpath=ancestor::*[self::div or self::section][1]"
            '//button[@aria-label="IA.COLLAPSE" or @aria-label="IA.EXPAND"]'
        ).first

    def section_has_toggle(self, section_label: str) -> bool:
        return self._get_named_section_toggle(section_label).count() > 0

    def is_named_section_expanded(self, section_label: str) -> bool:
        # This component keeps aria-label="IA.COLLAPSE" even after collapsing,
        # so the chevron's accessible label is not a trustworthy state signal.
        # Use the section's actual body visibility instead.
        if "schedule" in section_label.lower():
            grid = self.frame.get_by_role("grid").first
            return grid.count() > 0 and grid.is_visible()
        name_input = self.frame.locator(self.NAME_INPUT).first
        if name_input.count():
            return name_input.is_visible()
        name_label = self.frame.get_by_text("Name", exact=True)
        return name_label.count() > 0 and name_label.last.is_visible()

    def collapse_named_section(self, section_label: str):
        if self.is_named_section_expanded(section_label):
            self._get_named_section_toggle(section_label).click()
            self.page.wait_for_timeout(300)

    def expand_named_section(self, section_label: str):
        if not self.is_named_section_expanded(section_label):
            self._get_named_section_toggle(section_label).click()
            self.page.wait_for_timeout(300)

    # ══════════════════════════════════════════════════════════════════════════
    # Delete confirmation modal
    # ══════════════════════════════════════════════════════════════════════════

    def get_delete_modal_title(self) -> str:
        return self.delete_dialog().get_by_role("heading").first.inner_text()

    def get_delete_modal_message(self) -> str:
        return self.delete_dialog().inner_text()

    def confirm_delete_in_modal(self):
        self.delete_dialog().get_by_role("button", name="Delete").first.click()

    def cancel_delete_in_modal(self):
        self.delete_dialog().get_by_role("button", name="Cancel").first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # Validation helpers
    # ══════════════════════════════════════════════════════════════════════════

    def get_first_validation_error(self):
        return self.frame.locator(self.VALIDATION_ERROR).first

    def get_error_banner_text(self) -> str:
        return self.frame.get_by_role("alert").first.inner_text()

    # ── Additions 2026-08-17 (release www-p303 / SNL_release_monthly / LME) ────

    # The regression requirement and current retest notes allow four decimal
    # places. Five or more decimal places must be rejected.
    RATE_MAX_DECIMALS = 4
    NOTES_MAX = 1000
    NAME_MAX = 200

    def error_banner_text(self) -> str:
        """Tolerant read — returns '' when no banner is present."""
        try:
            banner = self.frame.get_by_role("alert")
            return banner.first.inner_text(timeout=2_500).strip() if banner.count() else ""
        except Exception:
            return ""

    def has_inline_field_error(self) -> bool:
        return self.frame.locator('[aria-invalid="true"]').count() > 0

    def schedule_column_headers(self) -> list[str]:
        return [
            h.strip()
            for h in self.page.evaluate(
                """() => {const d = document.querySelector('iframe#iamain').contentDocument;
                    return [...d.querySelectorAll('[role=columnheader]')]
                        .map(e => (e.textContent || '').trim());}"""
            )
            if h.strip()
        ]

    def is_field_mandatory(self, label: str) -> bool:
        return self.page.evaluate(
            """(label) => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const norm = s => s.replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
                return [...d.querySelectorAll('label')]
                    .some(e => norm(e.textContent).replace(/\s*\*$/, '') === label
                            && norm(e.textContent).endsWith('*'));
            }""",
            label,
        )

    def field_labels(self) -> list[str]:
        return self.page.evaluate(
            """() => {const d = document.querySelector('iframe#iamain').contentDocument;
                return [...d.querySelectorAll('label')]
                    .map(e => e.textContent.replace(/ /g, ' ').trim())
                    .filter(t => t && t !== '*' && t.length < 60);}"""
        )

    def row_is_editable(self, row_index: int = 0) -> bool:
        """True when the schedule row's start-date / rate cells accept input."""
        return self.page.evaluate(
            """(i) => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const rows = [...d.querySelectorAll('[role=row]')].slice(1);
                const r = rows[i];
                if (!r) return false;
                return [...r.querySelectorAll('input')]
                    .some(e => !e.disabled && !e.readOnly);
            }""",
            row_index,
        )

    def untranslated_aria_keys(self) -> list[str]:
        """Raw resource keys (IA.*, ROW_*, BULK_SELECTED) leaking into the UI."""
        return self.page.evaluate(
            """() => {
                const d = document.querySelector('iframe#iamain').contentDocument;
                const hits = new Set();
                const bad = /^(IA\.[A-Z0-9_.]+|ROW_[A-Z_]+|BULK_SELECTED)$/;
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

    def start_recording_toasts(self):
        """Success toasts are short-lived; arm this before the action."""
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
                    (ms) => ms.forEach((m) => m.addedNodes.forEach(grab)));
                window.__toastObserver.observe(d.body, {childList: true, subtree: true});
            }"""
        )

    def wait_for_toast(self, timeout: int = 6_000) -> str:
        remaining = timeout
        while remaining > 0:
            try:
                hits = self.page.evaluate("() => window.__toasts || []")
            except Exception:
                hits = []
            if hits:
                return hits[0]
            self.page.wait_for_timeout(300)
            remaining -= 300
        return self.error_banner_text()

    def save_menu_options(self) -> list[str]:
        self._open_save_variants()
        items = self.frame.locator('[role="menuitem"], [role="dialog"] button')
        return [
            t for t in ((items.nth(i).inner_text() or "").strip()
                        for i in range(items.count())) if t
        ]

    def save_via(self, option: str):
        if option == "Save":
            self.save()
            return
        self._open_save_variants()
        target = self.frame.get_by_role("button", name=option).or_(
            self.frame.locator(f'[role="menuitem"]:has-text("{option}")'))
        target.first.click()

    def _open_save_variants(self):
        """Open the split Save menu without firing the main Save action."""
        caret = self.frame.locator('[aria-label="Save"] ~ button:visible')
        if caret.count():
            caret.first.click()
        else:
            self._open_header_more_actions()
        self.page.wait_for_timeout(500)
