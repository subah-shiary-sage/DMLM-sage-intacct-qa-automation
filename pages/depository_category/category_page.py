"""
category_page.py
Page Object for the Depository Account Category Create / View / Edit / Delete pages.

Selectors verified against live DOM on 2026-07-15 (DMLM entity).

Key behaviours discovered live:
  * Create page  : Save is a role="menuitem"; Cancel is a visible button;
                   fields = Name (required), Document sequence (picker), Description.
                   There is NO Status field on Create.
  * View page    : fields render as read-only text (no inputs). Status IS shown.
                   Edit / Delete / (nested) three-dot live under header "More actions".
                   The three-dot menu contains only "View audit trail".
  * Edit page    : Status is a custom combobox (not a native <select>).
                   Save / Cancel are collapsed into the header "More actions" overflow.
  * Delete modal : dialog "Delete depository account category" with Delete / Cancel.
  * Headings     : Create -> "Create depository account category"
                   Edit   -> "Edit depository account category: <ID>--<Name>"
                   View   -> "Depository account category: <ID>--<Name>"
"""

from typing import Optional
from ..base_page import BasePage


class DepositoryAccountCategoryPage(BasePage):

    # ── Field selectors ────────────────────────────────────────────────────────
    NAME_INPUT        = 'input[aria-label="Name"]'
    DOC_SEQ_INPUT     = 'input[aria-label="Document sequence"]'   # role="combobox" (picker)
    DESCRIPTION_INPUT = 'input[aria-label="Description"]'

    # ── Collapsible section ────────────────────────────────────────────────────
    SECTION_HEADER = "Depository account category information"
    SECTION_TOGGLE = 'button[aria-label="IA.COLLAPSE"], button[aria-label="IA.EXPAND"]'

    # ── Delete confirmation modal ──────────────────────────────────────────────
    DELETE_DIALOG = "Delete depository account category"

    # ── Validation errors (inline + toast) ─────────────────────────────────────
    VALIDATION_ERROR = '[aria-invalid="true"], [class*="error"], [role="alert"]'

    # ══════════════════════════════════════════════════════════════════════════
    # Page heading helpers
    # ══════════════════════════════════════════════════════════════════════════

    def get_page_title(self) -> str:
        return self.frame.locator("h1").first.inner_text()

    def wait_for_view_page(self, timeout: int = 15_000):
        """Wait for the read-only View page heading 'Depository account category: ...'."""
        self.frame.locator("h1").filter(
            has_text="Depository account category:"
        ).filter(has_not_text="Edit").filter(has_not_text="Create").first.wait_for(timeout=timeout)

    def wait_for_edit_page(self, timeout: int = 10_000):
        self.frame.get_by_role(
            "heading", name="Edit depository account category"
        ).wait_for(timeout=timeout)

    # ══════════════════════════════════════════════════════════════════════════
    # Form interactions (Create & Edit)
    # ══════════════════════════════════════════════════════════════════════════

    def fill_name(self, name: str):
        inp = self.frame.locator(self.NAME_INPUT).first
        inp.fill(name)
        inp.evaluate("el => el.blur()")   # commit the value (Vue change/blur handlers)

    def get_name_value(self) -> str:
        return self.frame.locator(self.NAME_INPUT).first.input_value()

    def fill_description(self, description: str):
        self.frame.locator(self.DESCRIPTION_INPUT).first.fill(description)

    def fill_document_sequence(self, doc_seq: str):
        """
        Document sequence is a picker (combobox) of existing sequences, not a free
        text field. This types the query and selects a matching option if present.

        Keep this compatibility wrapper for the older suite; ticket-focused tests
        use ``select_document_sequence`` when exact option availability matters.
        """
        self.select_document_sequence(doc_seq, required=False)

    def document_sequence_input(self):
        """The Document sequence search/picker input on Create or Edit."""
        return self.frame.locator(self.DOC_SEQ_INPUT).first

    def get_document_sequence_value(self) -> str:
        """Return the editable picker value currently displayed on the form."""
        return self.document_sequence_input().input_value()

    def is_document_sequence_editable(self) -> bool:
        """Whether the Document sequence picker allows editing on this form."""
        return self.document_sequence_input().is_editable()

    def is_document_sequence_displayed(self, doc_seq: str) -> bool:
        """Whether the exact Document sequence value is visible on the current page."""
        value = self.frame.get_by_text(doc_seq, exact=True).first
        return value.count() > 0 and value.is_visible()

    def document_sequence_option(self, doc_seq: str):
        """Exact option for ``doc_seq`` in the currently open picker."""
        return self.frame.get_by_role("option", name=doc_seq, exact=True)

    def get_visible_document_sequence_options(
        self, queries: tuple[str, ...] = (), timeout: int = 8_000
    ) -> list[str]:
        """Enumerate visible options, including search-as-you-type query results."""
        combo = self.open_document_sequence_picker()
        visible = []

        def collect_options():
            options = self.frame.locator('[role="option"], [role="listitem"]')
            for index in range(options.count()):
                option = options.nth(index)
                if not option.is_visible():
                    continue
                text = option.inner_text().strip()
                if text and text.lower() not in {"add", "create new"} and text not in visible:
                    visible.append(text)

        collect_options()
        for query in queries:
            combo.fill("")
            combo.press_sequentially(query, delay=50)
            exact_text = self.frame.get_by_text(query, exact=True)
            try:
                exact_text.first.wait_for(state="visible", timeout=timeout)
            except Exception:
                pass
            collect_options()
            for index in range(exact_text.count()):
                candidate = exact_text.nth(index)
                if candidate.is_visible() and query not in visible:
                    visible.append(query)
                    break
        return visible

    def open_document_sequence_picker(self, query: str = ""):
        """Open the picker and optionally filter it without selecting a value."""
        combo = self.document_sequence_input()
        combo.click()
        if query:
            combo.fill(query)
        return combo

    def select_document_sequence(
        self, doc_seq: str, *, required: bool = True, timeout: int = 8_000
    ) -> bool:
        """
        Select an exact Document sequence option.

        Returns ``False`` when the sequence is not offered. ``required=True`` raises,
        which lets IADSSL-1792 assert that a sequence already owned by another
        category remains visible and selectable before Save performs validation.
        """
        self.open_document_sequence_picker(doc_seq)
        option = self.document_sequence_option(doc_seq)
        try:
            option.first.wait_for(state="visible", timeout=timeout)
        except Exception:
            option = self.frame.get_by_text(doc_seq, exact=True)
            try:
                option.first.wait_for(state="visible", timeout=timeout)
            except Exception:
                if required:
                    raise AssertionError(
                        f"Document sequence '{doc_seq}' was not offered by the picker"
                    )
                return False
        option.first.click()
        return True

    def select_first_available_document_sequence(self, timeout: int = 8_000) -> str:
        """Select and return the first real, currently available sequence option."""
        self.open_document_sequence_picker()
        options = self.frame.get_by_role("option")
        options.first.wait_for(state="visible", timeout=timeout)
        for index in range(options.count()):
            option = options.nth(index)
            text = option.inner_text().strip()
            if text and text.lower() not in {"add", "create new"}:
                option.click()
                return text
        raise AssertionError("No available Document sequence option was found")

    def clear_document_sequence(self):
        """Clear the editable picker value and commit the change."""
        combo = self.document_sequence_input()
        combo.fill("")
        combo.evaluate("el => el.blur()")

    def save_and_get_document_sequence_result(
        self, timeout: int = 15_000
    ) -> tuple[str, str]:
        """Save and return ``(saved|duplicate|validation, visible_message)``."""
        self.save()
        view_heading = self.frame.locator("h1").filter(
            has_text="Depository account category:"
        ).filter(has_not_text="Edit").filter(has_not_text="Create").first
        validation = self.frame.locator(
            '[aria-invalid="true"]:visible, [class*="error"]:visible, '
            '[role="alert"]:visible'
        ).first
        view_heading.or_(validation).first.wait_for(state="visible", timeout=timeout)
        if view_heading.is_visible():
            return "saved", ""
        message = self.get_alert_text()
        if "another depository category exists with this document sequence" in message.lower():
            return "duplicate", message
        return "validation", message

    def recover_document_sequence_form(self):
        """Reset the picker after a rejected Save so another option can be tried."""
        self.page.keyboard.press("Escape")
        self.clear_document_sequence()
        self.document_sequence_input().wait_for(state="visible", timeout=8_000)

    def set_status(self, status: str):
        """
        Status is a custom combobox on the Edit page ('Active' / 'Inactive').
        Opens the dropdown and selects the option by label.
        """
        combo = self.frame.get_by_role("combobox", name="Status").first
        combo.click()
        self.page.wait_for_timeout(500)
        option = self.frame.get_by_role("option", name=status)
        if option.count() > 0:
            option.first.click()
        else:  # fallback: some builds render options as plain list items
            self.frame.get_by_text(status, exact=True).first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # Save / Cancel  (robust across Create menuitem vs Edit overflow)
    # ══════════════════════════════════════════════════════════════════════════

    def save(self):
        self.click_header_action("Save")

    def cancel(self):
        self.click_header_action("Cancel")

    # ══════════════════════════════════════════════════════════════════════════
    # View page actions
    # ══════════════════════════════════════════════════════════════════════════

    def click_edit(self):
        self.click_header_action("Edit")
        self.wait_for_edit_page()

    def click_delete(self):
        self.click_header_action("Delete")
        # Wait on the heading, not the dialog role element (see _delete_dialog).
        # `.last` because the session-scoped page can accumulate stale, unmounted
        # confirm-dialog instances from earlier tests; the live one renders last.
        self.frame.get_by_role("heading", name=self.DELETE_DIALOG).last.wait_for(timeout=10_000)

    def click_back_to_list(self):
        link = self.frame.get_by_role("link", name="Depository account categories")
        if link.count() > 0 and link.first.is_visible():
            link.first.click()
        else:
            self.frame.get_by_role(
                "button", name="Back to previous page"
            ).first.click()
        self.frame.get_by_role(
            "heading", name="Depository account categories"
        ).wait_for(timeout=10_000)

    def is_name_readonly(self) -> bool:
        """On the View page the Name renders as text (no editable input)."""
        return self.frame.locator(self.NAME_INPUT).count() == 0

    def get_field_text(self, field_label: str) -> str:
        """Displayed value for a read-only field, matched by its accessible name."""
        return self.frame.get_by_label(field_label).first.inner_text()

    # ══════════════════════════════════════════════════════════════════════════
    # Three-dot menu (View page) — nested inside header "More actions"
    # ══════════════════════════════════════════════════════════════════════════

    def open_view_three_dot_menu(self):
        """Header More actions → nested More actions (the three-dot overflow).

        Once the header popover is open both "More actions" controls are visible;
        the nested three-dot is the *last* one in DOM order.
        """
        self._open_header_more_actions()
        self.frame.locator('[aria-label="More actions"]:visible').last.click()
        self.page.wait_for_timeout(400)

    def get_three_dot_menu_items(self) -> list[str]:
        self.open_view_three_dot_menu()
        # Options in the nested overflow render as buttons in a dialog.
        dialogs = self.frame.get_by_role("dialog")
        items = dialogs.last.get_by_role("button").all()
        return [i.inner_text().strip() for i in items if i.inner_text().strip()]

    def click_view_audit_trail(self):
        self.open_view_three_dot_menu()
        self.frame.get_by_role("button", name="View audit trail").first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # Document Sequence drilldown (View page)
    # ══════════════════════════════════════════════════════════════════════════

    def click_document_sequence_link(self):
        self.frame.locator(
            f'{self.DOC_SEQ_INPUT}, a[href*="docseq"], [data-drillable="true"]'
        ).first.click()

    # ══════════════════════════════════════════════════════════════════════════
    # Collapsible section
    # ══════════════════════════════════════════════════════════════════════════

    def _get_section_toggle(self):
        return self.frame.locator(self.SECTION_TOGGLE).first

    def is_section_expanded(self) -> bool:
        label = self._get_section_toggle().get_attribute("aria-label") or ""
        return "COLLAPSE" in label.upper()

    def minimize_section(self):
        if self.is_section_expanded():
            self._get_section_toggle().click()
            self.page.wait_for_timeout(400)

    def maximize_section(self):
        if not self.is_section_expanded():
            self._get_section_toggle().click()
            self.page.wait_for_timeout(400)

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

    def get_alert_text(self) -> str:
        """Return all visible validation/toast text as one normalized string."""
        alerts = self.frame.locator('[role="alert"]:visible')
        return "\n".join(
            alerts.nth(index).inner_text().strip()
            for index in range(alerts.count())
            if alerts.nth(index).inner_text().strip()
        )

    def get_category_id_from_url(self) -> Optional[str]:
        import re
        url = self.page.url
        match = re.search(r'[?&]key=(\w+)', url) or re.search(r'/(\d+)(?:\?|$)', url)
        return match.group(1) if match else None
