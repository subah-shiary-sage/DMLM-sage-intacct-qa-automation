"""Focused UI automation for IADSSL-1792.

The ticket changes Depository Account Category edit behavior.  These tests use
only the Sage Intacct UI and keep UI mechanics in the existing POM.
"""

import os
import uuid
from dataclasses import dataclass

import pytest

from pages.depository_category.category_page import DepositoryAccountCategoryPage
from pages.depository_category.listing_page import DepositoryAccountCategoryListingPage


pytestmark = pytest.mark.jira_iadssl_1792
KNOWN_USED_SEQUENCE = "17--Order Activation"


@dataclass(frozen=True)
class SequenceInventory:
    available: str | None
    rejected_used: str | None
    attempted: tuple[str, ...]


def _name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


def _create_category(listing, name: str, document_sequence: str | None = None):
    listing.navigate_to_list()
    listing.click_create()
    category = DepositoryAccountCategoryPage(listing.page)
    category.fill_name(name)
    if document_sequence:
        category.select_document_sequence(document_sequence)
    category.save()
    category.wait_for_view_page()
    return category


def _delete_if_present(listing, name: str):
    try:
        listing.navigate_to_list()
        listing.search_by_name(name)
        if listing.is_record_visible(name):
            listing.open_record_by_name(name)
            category = DepositoryAccountCategoryPage(listing.page)
            category.click_delete()
            category.confirm_delete_in_modal()
    except Exception:
        # Best-effort cleanup; cleanup failure must not hide the tested result.
        pass


@pytest.fixture(scope="module")
def sequence_inventory(authenticated_page):
    """Find usable and used sequences through finite UI-only create attempts."""
    listing = DepositoryAccountCategoryListingPage(authenticated_page)
    probe_name = _name("I1792_SEQ_PROBE")
    successful = None
    rejected_used = None

    listing.navigate_to_list()
    listing.click_create()
    probe = DepositoryAccountCategoryPage(listing.page)
    probe.fill_name(probe_name)
    candidates = probe.get_visible_document_sequence_options((KNOWN_USED_SEQUENCE,))
    assert candidates, (
        "Automation blocker: the picker did not expose the Jira-evidenced sequence "
        f"'{KNOWN_USED_SEQUENCE}' after exact search"
    )

    attempted = set()
    try:
        for candidate in candidates:
            if candidate in attempted:
                continue
            attempted.add(candidate)
            probe.select_document_sequence(candidate)
            result, message = probe.save_and_get_document_sequence_result()
            if result == "saved":
                successful = candidate
                break
            if result == "duplicate" and rejected_used is None:
                rejected_used = candidate
            assert result == "duplicate", (
                f"Unexpected validation while probing Document Sequence '{candidate}': "
                f"{message or '(no visible message)'}"
            )
            probe.recover_document_sequence_form()
    finally:
        if successful:
            _delete_if_present(listing, probe_name)

    return SequenceInventory(successful, rejected_used, tuple(attempted))


class TestIADSSL1792UnassignedCategory:
    def test_unassigned_category_accepts_unique_sequence(
        self, category_listing_page, sequence_inventory, steps
    ):
        """I1792-DAC-005/010 — unique sequence succeeds without assignment warning."""
        listing = category_listing_page
        category_name = _name("I1792_UNASSIGNED_POSITIVE")
        assert sequence_inventory.available, (
            "Automation/test-data blocker: all enumerated visible Document Sequence "
            f"candidates were attempted once without a successful save: "
            f"{sequence_inventory.attempted}"
        )
        try:
            _create_category(listing, category_name)
            listing.navigate_to_list()
            listing.search_by_name(category_name)
            listing.open_record_by_name(category_name)
            category = DepositoryAccountCategoryPage(listing.page)
            category.click_edit()
            category.select_document_sequence(sequence_inventory.available)
            steps.append(
                f"Selected UI-proven available sequence {sequence_inventory.available}"
            )
            result, message = category.save_and_get_document_sequence_result()

            assert result == "saved", message
            assert category.is_document_sequence_displayed(sequence_inventory.available)
            assert "cannot update document sequence after being assigned" not in message.lower()
            steps.append("Saved the unassigned category with the available sequence")
        finally:
            _delete_if_present(listing, category_name)

    def test_unassigned_category_rejects_used_sequence(
        self, category_listing_page, sequence_inventory, steps
    ):
        """I1792-DAC-006 — a sequence owned by another category is rejected."""
        listing = category_listing_page
        owner_name = _name("I1792_SEQ_OWNER")
        target_name = _name("I1792_UNASSIGNED")
        used_sequence = sequence_inventory.rejected_used
        created_owner = False
        try:
            if used_sequence is None:
                assert sequence_inventory.available, (
                    "Automation blocker: no duplicate-rejected or successful visible "
                    "Document Sequence candidate was discovered"
                )
                _create_category(listing, owner_name, sequence_inventory.available)
                used_sequence = sequence_inventory.available
                created_owner = True
                steps.append(f"Created sequence-owner category {owner_name}")
            else:
                steps.append(f"Reused probe-rejected sequence {used_sequence}")

            _create_category(listing, target_name)
            steps.append(f"Created unassigned target category {target_name}")
            listing.navigate_to_list()
            listing.search_by_name(target_name)
            listing.open_record_by_name(target_name)
            target = DepositoryAccountCategoryPage(listing.page)
            target.click_edit()

            target.select_document_sequence(used_sequence, required=True)
            assert target.get_document_sequence_value() == used_sequence
            steps.append("Confirmed the already-used sequence remained visible and selectable")

            result, message = target.save_and_get_document_sequence_result()
            alert = message.lower()
            assert result == "duplicate"
            assert "another depository category exists with this document sequence" in alert
            assert "cannot update document sequence after being assigned" not in alert
            steps.append("Confirmed Save rejected the duplicate-sequence assignment")
        finally:
            _delete_if_present(listing, target_name)
            if created_owner:
                _delete_if_present(listing, owner_name)


class TestIADSSL1792AssignedCategory:
    @pytest.fixture()
    def assigned_category(self, category_listing_page):
        name = os.getenv("IADSSL_1792_ASSIGNED_CATEGORY", "").strip()
        if not name:
            pytest.skip(
                "Test-data blocker: set IADSSL_1792_ASSIGNED_CATEGORY to a category "
                "used by an existing depository account"
            )
        listing = category_listing_page
        listing.navigate_to_list()
        listing.search_by_name(name)
        if not listing.is_record_visible(name):
            pytest.skip(f"Test-data blocker: assigned category '{name}' is not visible")
        listing.open_record_by_name(name)
        category = DepositoryAccountCategoryPage(listing.page)
        category.click_edit()
        return category, name

    def test_assigned_category_rejects_sequence_change(
        self, assigned_category, sequence_inventory, steps
    ):
        """I1792-DAC-008/011/013 — assigned category keeps its current sequence."""
        category, name = assigned_category
        current = category.get_document_sequence_value()
        steps.append(f"Opened assigned category {name} with sequence {current}")
        if not category.is_document_sequence_editable():
            # A disabled field is a valid UI implementation of the protection.
            return
        replacement = sequence_inventory.available
        assert replacement, (
            "Automation/test-data blocker: no successful Document Sequence candidate "
            f"was found after trying {sequence_inventory.attempted}"
        )
        assert replacement != current
        category.select_document_sequence(replacement)
        category.save()
        alert = category.get_alert_text().lower()
        assert "cannot update document sequence after being assigned" in alert
        assert category.get_document_sequence_value() in {current, replacement}
        steps.append("Confirmed the assigned-category update was blocked")

    def test_assigned_category_rejects_sequence_removal(
        self, assigned_category, steps
    ):
        """I1792-DAC-009 — assigned category cannot clear its document sequence."""
        category, name = assigned_category
        current = category.get_document_sequence_value()
        steps.append(f"Opened assigned category {name} with sequence {current}")
        if not category.is_document_sequence_editable():
            return
        category.clear_document_sequence()
        category.save()
        alert = category.get_alert_text().lower()
        assert "cannot update document sequence after being assigned" in alert
        steps.append("Confirmed clearing the assigned sequence was blocked")
