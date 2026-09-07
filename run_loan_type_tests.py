#!/usr/bin/env python
"""
run_loan_type_tests.py — Run one, several, or all Loan Type tests, with
every test listed individually by its full-sentence name.

This is a thin front door onto the same engine run_tests.bat / run_tests.ps1
use (`python -m pytest ...`); it exists so a single test can be picked from a
menu without typing/copy-pasting its full nodeid.

Usage:
    python run_loan_type_tests.py                # interactive menu
    python run_loan_type_tests.py --all           # run all 94 tests
    python run_loan_type_tests.py --list          # print the numbered menu and exit
    python run_loan_type_tests.py --stage create  # run one lifecycle stage
                                                    # (list | create | view | edit | delete)
    python run_loan_type_tests.py 45               # run menu item #45
    python run_loan_type_tests.py 12 45 80         # run several menu items
    python run_loan_type_tests.py -k interest_type # pass any extra pytest args through

Reports are written to reports\\report.html and reports\\results.xml
(see pytest.ini). Set HEADLESS=false in .env to watch the browser.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (menu label, stage, file, class, test function name)
# Kept as an explicit list (not re-discovered via pytest --collect-only) so
# the menu prints instantly and numbering stays stable between runs.
TESTS: list[tuple[str, str, str, str]] = [
    # ── List (Loan types list page) ─────────────────────────────────────────
    ("list", "test_list.py", "TestLoanTypeList", "test_the_list_page_loads_with_the_heading_loan_types"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_create_action_is_available_on_the_toolbar"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_grid_shows_the_loan_type_interest_calculation_method_and_description_columns"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_loan_type_name_filter_shows_the_contains_placeholder"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_revolving_non_revolving_type_filter_column_is_a_combobox"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_grid_shows_at_least_one_record"),
    ("list", "test_list.py", "TestLoanTypeList", "test_filtering_by_an_existing_name_shows_that_record"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_toolbar_delete_button_is_disabled_when_no_row_is_selected"),
    ("list", "test_list.py", "TestLoanTypeList", "test_selecting_a_row_enables_the_toolbar_delete_button"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_select_all_checkbox_selects_every_row_and_enables_delete"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_pagination_area_shows_the_total_item_count"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_manage_view_button_is_visible"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_filters_button_is_visible"),
    ("list", "test_list.py", "TestLoanTypeList", "test_the_list_view_and_split_view_toggle_buttons_are_present"),

    # ── Create ───────────────────────────────────────────────────────────────
    ("create", "test_create.py", "TestCreateLoanType", "test_the_loan_type_name_field_is_present_on_the_create_form"),
    ("create", "test_create.py", "TestCreateLoanType", "test_saving_with_an_empty_loan_type_name_is_blocked_and_keeps_the_user_on_the_create_form"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_description_field_is_optional_and_has_no_required_asterisk"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_type_field_shows_revolving_and_non_revolving_radio_options"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_interest_type_dropdown_contains_compound_and_simple_options"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_interest_calculation_method_field_appears_and_is_required_once_type_is_selected"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_interest_calculation_method_dropdown_offers_actual_365_and_actual_360_for_revolving_type"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_interest_calculation_method_dropdown_offers_actual_365_actual_360_and_30_360_for_non_revolving_type"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_order_entry_transaction_definition_field_shows_a_required_asterisk"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_item_for_loan_principal_posting_field_shows_a_required_asterisk"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_item_for_loan_interest_posting_field_shows_a_required_asterisk"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_add_row_button_is_present_in_the_payment_priority_order_section"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_payment_priority_grid_has_sort_order_type_and_fee_type_columns_on_create"),
    ("create", "test_create.py", "TestCreateLoanType", "test_clicking_add_row_increments_the_payment_priority_grid_by_one_row"),
    ("create", "test_create.py", "TestCreateLoanType", "test_clicking_remove_row_decrements_the_payment_priority_grid"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_fee_type_field_is_disabled_when_the_row_type_is_interest"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_fee_type_field_is_enabled_when_the_row_type_is_fee"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_save_button_is_visible_on_the_create_form"),
    ("create", "test_create.py", "TestCreateLoanType", "test_clicking_cancel_discards_changes_and_returns_to_the_loan_types_list"),
    ("create", "test_create.py", "TestCreateLoanType", "test_saving_with_zero_payment_priority_rows_shows_a_validation_error"),
    ("create", "test_create.py", "TestCreateLoanType", "test_saving_a_payment_priority_row_with_an_empty_sort_order_shows_a_validation_error"),
    ("create", "test_create.py", "TestCreateLoanType", "test_a_fully_valid_loan_type_saves_successfully_and_opens_the_view_page"),
    ("create", "test_create.py", "TestCreateLoanType", "test_a_non_revolving_loan_type_saves_successfully_with_one_principal_row_and_one_interest_row"),
    ("create", "test_create.py", "TestCreateLoanType", "test_a_non_revolving_loan_type_is_rejected_on_save_when_only_a_fee_row_is_present"),
    ("create", "test_create.py", "TestCreateLoanType", "test_a_stale_fee_type_value_left_after_switching_a_row_away_from_fee_blocks_save_until_cleared"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_save_split_button_dropdown_offers_exactly_save_save_and_close_and_save_and_new"),
    ("create", "test_create.py", "TestCreateLoanType", "test_clicking_save_and_new_saves_the_record_and_reopens_a_blank_create_form"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_loan_type_information_section_is_expanded_by_default"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_loan_invoicing_defaults_section_is_collapsed_by_default"),
    ("create", "test_create.py", "TestCreateLoanType", "test_the_sort_order_field_rejects_non_numeric_input"),
    ("create", "test_create.py", "TestCreateLoanType", "test_saving_with_duplicate_sort_order_values_across_rows_shows_a_validation_error"),
    ("create", "test_create.py", "TestCreateLoanType", "test_a_second_payment_priority_row_with_type_principal_is_rejected_on_save"),
    ("create", "test_create.py", "TestCreateLoanType", "test_a_second_payment_priority_row_with_type_interest_is_rejected_on_save"),
    ("create", "test_create.py", "TestCreateLoanType", "test_multiple_payment_priority_rows_with_type_fee_are_allowed_and_save_successfully"),
    ("create", "test_create.py", "TestCreateLoanType", "test_a_newly_added_payment_priority_row_is_immediately_editable"),
    ("create", "test_create.py", "TestCreateLoanType", "test_saving_a_completely_empty_create_form_is_blocked_by_mandatory_field_validation"),
    ("create", "test_create.py", "TestCreateLoanType", "test_clicking_cancel_with_unsaved_changes_discards_them_immediately_with_no_confirmation_prompt"),

    # ── View ─────────────────────────────────────────────────────────────────
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_view_page_displays_the_loan_type_name"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_view_page_displays_the_type_value"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_view_page_displays_the_interest_type_value"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_view_page_displays_the_interest_calculation_method_value"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_view_page_shows_status_active"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_loan_invoicing_defaults_section_is_visible"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_payment_priority_order_section_is_visible"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_payment_priority_grid_has_sort_order_type_and_fee_type_columns_on_view"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_edit_button_is_visible_on_the_detail_page"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_delete_button_is_visible_on_the_detail_page"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_three_dot_menu_contains_view_audit_trail"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_loan_types_breadcrumb_link_navigates_back_to_the_list"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_back_arrow_navigates_to_the_loan_types_list"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_three_dot_menu_is_missing_the_object_definition_entry"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_loan_type_information_fields_are_not_editable_on_the_view_page"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_payment_priority_grid_is_read_only_on_the_view_page"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_page_footer_shows_a_privacy_policy_link_and_copyright_text"),
    ("view", "test_view_and_delete.py", "TestViewLoanType", "test_the_view_page_data_matches_the_values_entered_during_creation"),

    # ── Delete ───────────────────────────────────────────────────────────────
    ("delete", "test_view_and_delete.py", "TestDeleteLoanType", "test_clicking_delete_opens_the_confirmation_modal"),
    ("delete", "test_view_and_delete.py", "TestDeleteLoanType", "test_the_delete_modal_message_names_the_record_and_says_it_will_be_deleted"),
    ("delete", "test_view_and_delete.py", "TestDeleteLoanType", "test_confirming_delete_permanently_removes_the_record_from_the_list"),
    ("delete", "test_view_and_delete.py", "TestDeleteLoanType", "test_clicking_cancel_in_the_modal_closes_it_without_deleting_the_record"),
    ("delete", "test_view_and_delete.py", "TestDeleteLoanType", "test_deleting_from_the_view_page_redirects_to_the_loan_types_list"),
    ("delete", "test_view_and_delete.py", "TestDeleteLoanType", "test_a_loan_type_not_assigned_to_any_loan_account_deletes_successfully"),

    # ── Edit ─────────────────────────────────────────────────────────────────
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_edit_form_pre_populates_the_loan_type_name"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_edit_form_pre_populates_the_description_and_keeps_it_editable"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_type_field_is_read_only_plain_text_in_edit_mode"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_edit_form_pre_populates_the_interest_type"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_edit_form_pre_populates_the_interest_calculation_method"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_edit_form_pre_populates_the_status"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_clearing_the_loan_type_name_and_saving_keeps_the_user_in_edit_mode"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_cancelling_the_edit_does_not_save_changes_and_retains_the_original_name"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_payment_priority_rows_are_pre_populated_in_edit_mode"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_save_button_is_visible_when_the_header_more_actions_overflow_is_opened"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_saving_an_updated_loan_type_name_persists_the_change_on_the_view_page"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_edit_page_title_is_user_friendly_and_does_not_expose_the_internal_object_path"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_status_dropdown_offers_active_and_inactive_options"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_interest_type_mandatory_marker_on_edit_matches_the_marker_on_create"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_interest_calculation_method_mandatory_marker_on_edit_matches_the_marker_on_create"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_the_edit_page_loads_type_interest_calculation_method_and_status_fully_populated"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_editing_a_revolving_loan_type_requires_keeping_at_least_one_interest_row"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_editing_a_non_revolving_loan_type_requires_keeping_both_a_principal_row_and_an_interest_row"),
    ("edit", "test_edit.py", "TestEditLoanType", "test_navigating_away_via_the_back_arrow_without_saving_discards_unsaved_changes"),
]

STAGES = ("list", "create", "view", "edit", "delete")


def nodeid(entry: tuple[str, str, str, str]) -> str:
    _stage, fname, cls, fn = entry
    return f"tests/loan_type/{fname}::{cls}::{fn}"


def find_python() -> Path:
    candidate = Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python310" / "python.exe"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def print_menu() -> None:
    stage_titles = {
        "list": "LIST  (TC-LT-001 - 014)",
        "create": "CREATE  (TC-LT-028 - 046, 057 - 058, 064 - 078)",
        "view": "VIEW  (TC-LT-015 - 027, 079 - 083)",
        "delete": "DELETE  (TC-LT-059 - 063, 084)",
        "edit": "EDIT  (TC-LT-047 - 056, 085 - 092)",
    }
    n = 0
    current_stage = None
    for entry in TESTS:
        n += 1
        stage = entry[0]
        if stage != current_stage:
            current_stage = stage
            print(f"\n-- {stage_titles[stage]} --")
        _stage, _fname, _cls, fn = entry
        print(f"  {n:>3}. {fn}")
    print(f"\n{len(TESTS)} tests total.")


def run(nodeids: list[str], extra_args: list[str]) -> int:
    python_exe = find_python()
    cmd = [str(python_exe), "-m", "pytest", *nodeids, *extra_args]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    print("\n----------------------------------------------------------------------")
    print("Done. HTML report: reports\\report.html")
    print("----------------------------------------------------------------------")
    return result.returncode


def main() -> int:
    args = sys.argv[1:]

    if not args:
        print_menu()
        print(
            "\nEnter test numbers to run (space-separated), 'a' for all, or "
            "Enter to cancel:"
        )
        choice = input("> ").strip()
        if not choice:
            print("Cancelled.")
            return 0
        if choice.lower() in ("a", "all"):
            return run([nodeid(e) for e in TESTS], [])
        try:
            picks = [int(x) for x in choice.split()]
        except ValueError:
            print(f"Not a valid selection: {choice!r}")
            return 1
        bad = [p for p in picks if not (1 <= p <= len(TESTS))]
        if bad:
            print(f"Out of range (1-{len(TESTS)}): {bad}")
            return 1
        return run([nodeid(TESTS[p - 1]) for p in picks], [])

    if args[0] == "--list":
        print_menu()
        return 0

    if args[0] == "--all":
        return run([nodeid(e) for e in TESTS], args[1:])

    if args[0] == "--stage":
        if len(args) < 2 or args[1] not in STAGES:
            print(f"--stage requires one of: {', '.join(STAGES)}")
            return 1
        stage = args[1]
        picked = [e for e in TESTS if e[0] == stage]
        return run([nodeid(e) for e in picked], args[2:])

    # Numeric args -> menu indices; anything else passed straight through to pytest.
    numeric_args = []
    passthrough_args = []
    for a in args:
        if a.isdigit():
            numeric_args.append(int(a))
        else:
            passthrough_args.append(a)

    if numeric_args:
        bad = [p for p in numeric_args if not (1 <= p <= len(TESTS))]
        if bad:
            print(f"Out of range (1-{len(TESTS)}): {bad}")
            return 1
        return run([nodeid(TESTS[p - 1]) for p in numeric_args], passthrough_args)

    # No numeric picks — treat everything as extra pytest args scoped to loan_type.
    return run(["tests/loan_type"], passthrough_args)


if __name__ == "__main__":
    raise SystemExit(main())
