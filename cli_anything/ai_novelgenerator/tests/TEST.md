# Test Plan

## Test Inventory Plan

- `test_core.py`: 27 unit tests planned
- `test_full_e2e.py`: 18 E2E tests planned

### `roles.py`

- Test role-library category discovery, role CRUD, moves, file imports, `character_state.txt` analysis/import, and prompt-injection helpers
- Edge cases: duplicate names, cross-category resolution, temp-library writes, and prompt replacement when named roles are present or absent
- Expected test count: 8

## Unit Test Plan

### `project.py`

- Test project creation, save/load, status reporting, important path derivation, and compatibility wrappers for `create/open/save/info/list_profiles`
- Edge cases: empty workspace, missing generated files
- Expected test count: 5

### `session.py`

- Test locked JSON save path, workspace snapshot capture/restore, undo/redo state flow
- Edge cases: no snapshots, deleted files restored from snapshot
- Expected test count: 3

### `export.py`

- Test bundle export creates valid ZIP with manifest and project file plus compatibility `render()` dispatch and preset discovery
- Edge cases: overwrite behavior, magic-byte verification, and unknown preset rejection
- Expected test count: 3

### `ai_novelgenerator_backend.py`

- Test runtime config binding and deterministic mock adapter behavior
- Edge cases: missing profile names
- Expected test count: 1

### `configuration.py`

- Test `config.json` CRUD for LLM and embedding profiles, choose-config inspection/set, deletion guards for selected profiles, rename propagation into `choose_configs`, and single-profile JSON import that preserves extra metadata fields
- Edge cases: deleting an in-use profile, no-op updates, missing names, import overwrite behavior, and direct persistence verification in the JSON file on disk
- Expected test count: 3

### `inspection.py`

- Test parsed chapter metadata inspection and prompt-building wrappers
- Edge cases: prompt inspection after prior chapter finalization, JSON-safe prompt generation, resumable partial-architecture progress, plot-arc review context visibility
- Expected test count: 4

### `generation.py`

- Test batch chapter generation across a numeric range with optional finalization, skip-existing behavior, draft/finalized skip policies, blueprint-range clamping, auto-enrich thresholds, continue-from-next-unfinished flow, and chapter-state inspection
- Edge cases: multi-chapter file creation, skipped draft vs finalized chapter files, blueprint-clamped ranges, enrichment trigger thresholds, aggregate result shape, and `missing/draft/finalized` state classification
- Expected test count: 7

### `review.py`

- Test consistency review wrapper includes `plot_arcs.txt` context when present while keeping JSON-safe output
- Edge cases: empty plot-arcs file, subprocess JSON cleanliness despite source-module debug prints
- Expected test count: 1

### `workspace.py`

- Test direct read/write round-trips for core workspace text files and chapter text files
- Edge cases: writing a chapter file before it exists, content previews, and metadata shape
- Expected test count: 2

## E2E Test Plan

- Create a real harness project file and workspace on disk
- Run architecture generation through the source modules
- Run blueprint generation and verify parseable chapter structure
- Generate and finalize a chapter, then verify summary/state/vector-store artifacts
- Build the next chapter prompt without mutating the workspace and verify parsed chapter metadata
- Inspect resumable `partial_architecture.json` state and `plot_arcs.txt` review context as direct probe commands
- Perform direct workspace text edits and verify the manual revision loop closes at both core and CLI layers
- Run batch chapter generation and verify multiple chapter files plus finalization side effects
- Export a final ZIP bundle and validate ZIP magic bytes and manifest presence
- Exercise the full role-library workflow, including category creation, role CRUD, file import, `character_state.txt` analysis/import, and prompt injection into chapter generation
- Exercise CLI subprocess config management for LLM/embedding list/show/create/update/rename/delete, single-profile JSON import, plus `choose_configs` inspection and persistence

### Config Management Flow

- Workflow name: `config-management-cli-roundtrip`
- Simulates: an agent maintaining the source app's shared `config.json` without opening the GUI settings panel
- Operations chained: create project -> import/update/rename/list/show LLM config -> import/show embedding config -> inspect/set choose config -> delete temporary profiles after switching defaults back
- Verified: machine-readable CRUD responses are stable, imported metadata survives round-trip persistence, selected slots are reported accurately, rename updates chosen references, and `config.json` is truly persisted on disk

## Config Management Expansion

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\�¿�\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 55 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  1%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [  3%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [  5%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [  7%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [  9%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 10%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 12%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 14%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_profile_crud_and_choose_persist_to_json PASSED [ 16%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_rename_updates_selected_choose_slots PASSED [ 18%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 20%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED [ 21%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED [ 23%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_role_library_crud_and_move PASSED [ 25%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_import_roles_from_file_parses_multiple_entries PASSED [ 27%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_analyze_and_import_roles_from_character_state PASSED [ 29%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_injects_role_library_content PASSED [ 30%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_generate_chapter_reports_included_roles PASSED [ 32%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_architecture_resume_state_reports_partial_progress PASSED [ 34%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_plot_arcs_context_reads_review_context PASSED [ 36%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_review_consistency_includes_plot_arcs_context PASSED [ 38%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED [ 40%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_skip_existing PASSED [ 41%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_clamp_to_blueprint_range PASSED [ 43%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_distinguishes_draft_and_finalized_skips PASSED [ 45%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_auto_enrich_low_word_drafts PASSED [ 47%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_next_unfinished_and_continue_batch_generation PASSED [ 49%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_can_clamp_and_skip_finalized PASSED [ 50%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_reports_when_no_chapter_can_resume PASSED [ 52%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_status_and_scan_report_missing_draft_finalized PASSED [ 54%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_finalized_chapter_summary PASSED [ 56%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_generate_blueprint_before_chapters PASSED [ 58%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_finalizing_existing_draft PASSED [ 60%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_complete_when_all_chapters_finalized PASSED [ 61%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_workspace_text_info_and_write_roundtrip PASSED [ 63%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_write_chapter_text_creates_editable_chapter_file PASSED [ 65%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 67%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 69%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 70%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED [ 72%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED [ 74%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_can_resume_from_next_chapter PASSED [ 76%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_architecture_resume_and_plot_arcs_inspection PASSED [ 78%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_workspace_text_editing_roundtrip PASSED [ 80%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 81%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [ 83%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED [ 85%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED [ 87%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_role_library_workflow_and_prompt_injection_json PASSED [ 89%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_continue_and_skip_existing_json PASSED [ 90%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_clamp_and_distinct_skip_modes_json PASSED [ 92%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_resume_and_review_context_commands_json PASSED [ 94%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_workspace_and_chapter_write_commands_json PASSED [ 96%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_chapter_status_scan_and_project_status_json PASSED [ 98%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_config_management_crud_and_choose_json PASSED [100%]

======================= 55 passed in 120.35s (0:02:00) ========================
```

Updated summary statistics:

- Total tests: 55
- Pass rate: 100%
- Execution time: 120.35s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, prompt inspection, architecture resume inspection, plot-arcs review context, direct workspace editing, chapter state inspection, batch generation/continue workflows, role-library CLI CRUD, and full `config.json` CRUD for LLM/embedding profiles plus choose-config persistence
- Covered: selected-profile protection on delete, choose-config rename propagation, and subprocess validation that config mutations are truly written to disk
- Covered: compatibility wrappers in `core.project` (`create/open/save/info/list_profiles`) and `core.export.render()` plus preset registry inspection through `EXPORT_PRESETS`
- Covered: CLI error handling is now centralized through decorator-based callback wrapping instead of per-command inline `try/except` blocks
- Remaining gap: live network-backed LLM and embedding providers are still not exercised; deterministic harness mocks continue to validate the real source pipeline without external API calls

### Role Library Flow

- Workflow name: `role-library-cli-roundtrip`
- Simulates: an agent managing the workspace role library entirely through CLI commands before generating chapters
- Operations chained: create project -> create categories -> create/import/analyze/import-state roles -> rename/move/delete roles -> inspect prompt/chapter generation with role injection
- Verified: role files are created under `角色库`, temp analysis output is materialized, machine-readable CRUD responses are stable, and generated prompts include selected role content

## Role Library Expansion

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\�¿�\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 52 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  1%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [  3%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [  5%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [  7%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [  9%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 11%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 13%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 15%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 17%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED [ 19%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED [ 21%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_role_library_crud_and_move PASSED [ 23%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_import_roles_from_file_parses_multiple_entries PASSED [ 25%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_analyze_and_import_roles_from_character_state PASSED [ 26%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_injects_role_library_content PASSED [ 28%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_generate_chapter_reports_included_roles PASSED [ 30%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_architecture_resume_state_reports_partial_progress PASSED [ 32%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_plot_arcs_context_reads_review_context PASSED [ 34%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_review_consistency_includes_plot_arcs_context PASSED [ 36%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED [ 38%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_skip_existing PASSED [ 40%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_clamp_to_blueprint_range PASSED [ 42%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_distinguishes_draft_and_finalized_skips PASSED [ 44%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_auto_enrich_low_word_drafts PASSED [ 46%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_next_unfinished_and_continue_batch_generation PASSED [ 48%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_can_clamp_and_skip_finalized PASSED [ 50%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_reports_when_no_chapter_can_resume PASSED [ 51%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_status_and_scan_report_missing_draft_finalized PASSED [ 53%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_finalized_chapter_summary PASSED [ 55%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_generate_blueprint_before_chapters PASSED [ 57%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_finalizing_existing_draft PASSED [ 59%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_complete_when_all_chapters_finalized PASSED [ 61%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_workspace_text_info_and_write_roundtrip PASSED [ 63%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_write_chapter_text_creates_editable_chapter_file PASSED [ 65%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 67%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 69%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 71%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED [ 73%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED [ 75%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_can_resume_from_next_chapter PASSED [ 76%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_architecture_resume_and_plot_arcs_inspection PASSED [ 78%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_workspace_text_editing_roundtrip PASSED [ 80%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 82%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [ 84%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED [ 86%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED [ 88%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_role_library_workflow_and_prompt_injection_json PASSED [ 90%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_continue_and_skip_existing_json PASSED [ 92%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_clamp_and_distinct_skip_modes_json PASSED [ 94%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_resume_and_review_context_commands_json PASSED [ 96%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_workspace_and_chapter_write_commands_json PASSED [ 98%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_chapter_status_scan_and_project_status_json PASSED [100%]

======================= 52 passed in 126.78s (0:02:06) ========================
```

Updated summary statistics:

- Total tests: 52
- Pass rate: 100%
- Execution time: 126.78s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, prompt inspection, architecture resume inspection, plot-arcs review context, direct workspace editing, chapter state inspection, batch generation/continue workflows, full role-library CLI CRUD, file import, `character_state.txt` analysis/import, and prompt injection verification at both core and subprocess CLI layers
- Covered: `project status` role-library summary reporting, including requested character names that are present or missing for prompt injection
- Remaining gap: live network-backed LLM and embedding providers are still not exercised; deterministic harness mocks continue to validate the real source pipeline without external API calls

## Realistic Workflow Scenarios

### Mocked Full Novel Bootstrap

- Workflow name: `bootstrap-first-chapter`
- Simulates: an agent starting a new long-form project and pushing it through first-chapter production
- Operations chained: create project -> generate architecture -> generate blueprint -> generate chapter 1 -> finalize chapter 1 -> consistency review -> export bundle
- Verified: native text files exist, blueprint is parseable, summary/state files update, bundle is a valid ZIP

### Installed CLI Subprocess Flow

- Workflow name: `installed-cli-roundtrip`
- Simulates: an agent using the installed PATH command from an arbitrary directory
- Operations chained: help -> project creation -> architecture -> blueprint -> chapter generation -> finalize -> export
- Verified: command resolution via `_resolve_cli`, JSON output structure, ZIP artifact creation

### Prompt Inspection Flow

- Workflow name: `inspect-before-generate`
- Simulates: an agent checking blueprint metadata and the exact chapter-generation prompt before producing chapter 2
- Operations chained: create project -> generate architecture -> generate blueprint -> generate/finalize chapter 1 -> inspect chapter info -> build chapter 2 prompt
- Verified: parsed chapter metadata is structured, prompt text is returned as JSON, optional prompt file is written to disk

### Batch Generation Flow

- Workflow name: `batch-generate-range`
- Simulates: an agent generating a contiguous chapter range after planning is complete
- Operations chained: create project -> generate architecture -> generate blueprint -> batch-generate chapters 1..2 -> optional finalize for each chapter
- Verified: multiple chapter files are created, JSON output stays machine-readable, finalization artifacts remain present after the batch run

### Resume Batch Flow

- Workflow name: `continue-from-next-unfinished`
- Simulates: an agent resuming a partially completed chapter run without regenerating existing chapter files
- Operations chained: create project -> generate architecture -> generate blueprint -> generate chapter 1 -> continue batch to chapter 3 -> re-run batch with `--skip-existing`
- Verified: resume starts at the next missing chapter, existing files are skipped deterministically, and machine-readable batch status reports generated/skipped counts

### Blueprint-Aware Batch Flow

- Workflow name: `blueprint-clamped-batch`
- Simulates: an agent requesting a broader chapter range than the current blueprint actually defines
- Operations chained: create project -> generate architecture -> write a partial blueprint -> batch-generate with `--clamp-to-blueprint`
- Verified: the batch range is clamped to the blueprint chapter numbers and the JSON result reports both requested and effective ranges

### Draft Versus Finalized Skip Flow

- Workflow name: `skip-draft-vs-finalized`
- Simulates: an agent revisiting a workspace containing a mix of raw drafts and finalized chapters
- Operations chained: create project -> generate architecture/blueprint -> generate multiple drafts -> finalize one chapter -> re-run batch with `--skip-drafts --skip-finalized`
- Verified: machine-readable status clearly distinguishes `skipped_draft` from `skipped_finalized`, backed by harness-managed chapter finalization state

### Chapter State Inspection Flow

- Workflow name: `inspect-chapter-state`
- Simulates: an agent checking which chapters are missing, drafted, or finalized before resuming work
- Operations chained: create project -> generate architecture/blueprint -> generate chapter 1 -> generate/finalize chapter 2 -> inspect `chapter status` -> inspect `chapter scan` -> inspect `project status`
- Verified: single-chapter and range-level state inspection report `missing/draft/finalized` correctly, and project status summarizes finalized chapter counts

## Batch Refinement Expansion

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\�¿�\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 35 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  2%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [  5%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [  8%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [ 11%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [ 14%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 17%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 20%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 22%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 25%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED [ 28%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED [ 31%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_architecture_resume_state_reports_partial_progress PASSED [ 34%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_plot_arcs_context_reads_review_context PASSED [ 37%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_review_consistency_includes_plot_arcs_context PASSED [ 40%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED [ 42%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_skip_existing PASSED [ 45%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_auto_enrich_low_word_drafts PASSED [ 48%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_next_unfinished_and_continue_batch_generation PASSED [ 51%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_workspace_text_info_and_write_roundtrip PASSED [ 54%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_write_chapter_text_creates_editable_chapter_file PASSED [ 57%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 60%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 62%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 65%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED [ 68%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED [ 71%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_can_resume_from_next_chapter PASSED [ 74%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_architecture_resume_and_plot_arcs_inspection PASSED [ 77%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_workspace_text_editing_roundtrip PASSED [ 80%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 82%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [ 85%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED [ 88%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED [ 91%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_continue_and_skip_existing_json PASSED [ 94%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_resume_and_review_context_commands_json PASSED [ 97%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_workspace_and_chapter_write_commands_json PASSED [100%]

======================== 35 passed in 66.86s (0:01:06) ========================
```

Updated summary statistics:

- Total tests: 35
- Pass rate: 100%
- Execution time: 66.86s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, prompt inspection, architecture resume inspection, plot-arcs review context, direct workspace editing, batch generation, skip-existing behavior, auto-enrich trigger logic, and continue-from-next-unfinished workflows at both core and CLI subprocess layers
- Remaining gap: live network-backed LLM and embedding providers are still not exercised; deterministic harness mocks continue to validate the real source pipeline without external API calls

### Resume And Review Context Flow

- Workflow name: `inspect-resume-and-review-context`
- Simulates: an agent resuming interrupted architecture generation and checking unresolved plot context before review
- Operations chained: create project -> seed `partial_architecture.json` -> inspect `generate architecture-state` -> inspect `review plot-arcs` -> run `review consistency`
- Verified: resume step detection is structured, plot-arc text is exposed as JSON, consistency review reports that plot arcs were included

### Workspace Edit Flow

- Workflow name: `manual-workspace-revision-loop`
- Simulates: an agent manually revising core text artifacts after generation without opening the GUI tabs
- Operations chained: create project -> generate architecture/blueprint -> `workspace write architecture` -> `workspace write blueprint` -> `chapter write 1`
- Verified: files are updated in place, JSON output includes path and content metadata, later commands observe the revised text

## Test Results

Command run:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\新坑\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.10.0, langsmith-0.4.25, cov-4.1.0
collecting ... collected 14 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  7%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [ 14%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [ 21%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [ 28%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [ 35%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 42%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 50%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 57%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 64%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 71%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 78%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 85%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 92%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [100%]

======================== 14 passed in 77.64s (0:01:17) ========================
```

## Summary Statistics

- Total tests: 14
- Pass rate: 100%
- Execution time: 77.64s

## Coverage Notes

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, full mocked generation pipeline, installed CLI subprocess invocation
- Gap: live external LLM and embedding providers are not exercised in CI-style tests; deterministic `HarnessMock` adapters are used to verify the real source pipeline without network dependencies

## Revalidation Results

After adding harness-side stubs for optional source-app dependencies used only by non-mock providers (`google.genai`, Azure SDK modules, `nltk`, and vector-store packages), the suite was re-run in the current environment.

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Result:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\新坑\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 14 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  7%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [ 14%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [ 21%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [ 28%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [ 35%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 42%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 50%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 57%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 64%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 71%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 78%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 85%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 92%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [100%]

============================= 14 passed in 13.09s =============================
```

## Prompt Inspection Expansion

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\新坑\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 18 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  5%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [ 11%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [ 16%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [ 22%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [ 27%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 33%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 38%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 44%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 50%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED [ 55%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED [ 61%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 66%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 72%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 77%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED [ 83%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 88%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [ 94%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED [100%]

============================= 18 passed in 28.60s =============================
```

Updated summary statistics:

- Total tests: 18
- Pass rate: 100%
- Execution time: 28.60s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, full mocked generation pipeline, installed CLI subprocess invocation, parsed blueprint inspection, prompt-preview generation, JSON-safe prompt export
- Remaining gap: existing CLI command surface is still broader than the focused prompt-inspection tests; batch generation and some session/config subcommands remain less exercised than the core generation path

## Batch Generation Expansion

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\新坑\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 21 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  4%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [  9%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [ 14%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [ 19%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [ 23%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 28%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 33%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 38%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 42%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED [ 47%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED [ 52%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED [ 57%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 61%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 66%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 71%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED [ 76%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED [ 80%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 85%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [ 90%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED [ 95%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED [100%]

============================= 21 passed in 45.27s =============================
```

Updated summary statistics:

- Total tests: 21
- Pass rate: 100%
- Execution time: 45.27s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, full mocked generation pipeline, installed CLI subprocess invocation, parsed blueprint inspection, prompt-preview generation, JSON-safe prompt export, batch chapter generation with optional per-chapter finalization
- Remaining gap: `config` and `session` subcommands still have lighter direct coverage than the main generation path, and resume-oriented `partial_architecture` introspection is not yet exposed as dedicated commands

## Resume And Review Context Expansion

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\�¿�\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 26 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  3%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [  7%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [ 11%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [ 15%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [ 19%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 23%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 26%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 30%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 34%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED [ 38%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED [ 42%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_architecture_resume_state_reports_partial_progress PASSED [ 46%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_plot_arcs_context_reads_review_context PASSED [ 50%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_review_consistency_includes_plot_arcs_context PASSED [ 53%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED [ 57%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 61%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 65%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 69%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED [ 73%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED [ 76%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_architecture_resume_and_plot_arcs_inspection PASSED [ 80%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 84%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [ 88%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED [ 92%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED [ 96%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_resume_and_review_context_commands_json PASSED [100%]

============================= 26 passed in 59.32s =============================
```

Updated summary statistics:

- Total tests: 26
- Pass rate: 100%
- Execution time: 59.32s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, full mocked generation pipeline, installed CLI subprocess invocation, parsed blueprint inspection, prompt-preview generation, JSON-safe prompt export, batch chapter generation with optional per-chapter finalization, resumable `partial_architecture` inspection, `plot_arcs.txt` review-context inspection, JSON-safe consistency review with plot-arc context inclusion
- Remaining gap: `config` and `session` subcommands still have lighter direct coverage than the main generation path, but the focused `partial_architecture` resume and `plot_arcs` inspection/review workflows are now exposed and covered

## Workspace Editing Expansion

Command run:

```bash
python -m pytest -v --tb=no cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\新坑\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... collected 30 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED [  3%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED [  6%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED [ 10%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED [ 13%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED [ 16%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED [ 20%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED [ 23%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED [ 26%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED [ 30%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED [ 33%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED [ 36%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_architecture_resume_state_reports_partial_progress PASSED [ 40%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_plot_arcs_context_reads_review_context PASSED [ 43%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_review_consistency_includes_plot_arcs_context PASSED [ 46%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED [ 50%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_workspace_text_info_and_write_roundtrip PASSED [ 53%]
cli_anything/ai_novelgenerator/tests/test_core.py::test_write_chapter_text_creates_editable_chapter_file PASSED [ 56%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules PASSED [ 60%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED [ 63%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED [ 66%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED [ 70%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED [ 73%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_architecture_resume_and_plot_arcs_inspection PASSED [ 76%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_workspace_text_editing_roundtrip PASSED [ 80%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 83%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json PASSED [ 86%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED [ 90%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED [ 93%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_resume_and_review_context_commands_json PASSED [ 96%]
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_workspace_and_chapter_write_commands_json PASSED [100%]

============================= 30 passed in 59.37s =============================
```

Updated summary statistics:

- Total tests: 30
- Pass rate: 100%
- Execution time: 59.37s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, full mocked generation pipeline, installed CLI subprocess invocation, parsed blueprint inspection, prompt-preview generation, JSON-safe prompt export, batch chapter generation with optional per-chapter finalization, resumable `partial_architecture` inspection, `plot_arcs.txt` review-context inspection, JSON-safe consistency review with plot-arc context inclusion, direct read/write loops for core workspace text files and chapter text files
- Remaining gap: `config` and `session` subcommands still have lighter direct coverage than the main generation and manual-revision paths, and role-library / environment-management features remain outside the current CLI surface

## Installed CLI Verification

Last run: 2026-05-02 17:16:56

Command run:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest -v -s --tb=short cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\�¿�\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... [_resolve_cli] Using installed command: C:\Users\18160\AppData\Roaming\Python\Python311\Scripts\cli-anything-ai-novelgenerator.EXE
collected 56 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_profile_crud_and_choose_persist_to_json PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_rename_updates_selected_choose_slots PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_import_profile_preserves_extra_metadata_fields PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_role_library_crud_and_move PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_import_roles_from_file_parses_multiple_entries PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_analyze_and_import_roles_from_character_state PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_injects_role_library_content PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_generate_chapter_reports_included_roles PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_architecture_resume_state_reports_partial_progress PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_plot_arcs_context_reads_review_context PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_review_consistency_includes_plot_arcs_context PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_skip_existing PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_clamp_to_blueprint_range PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_distinguishes_draft_and_finalized_skips PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_auto_enrich_low_word_drafts PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_next_unfinished_and_continue_batch_generation PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_can_clamp_and_skip_finalized PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_reports_when_no_chapter_can_resume PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_status_and_scan_report_missing_draft_finalized PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_finalized_chapter_summary PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_generate_blueprint_before_chapters PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_finalizing_existing_draft PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_complete_when_all_chapters_finalized PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_workspace_text_info_and_write_roundtrip PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_write_chapter_text_creates_editable_chapter_file PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules 
  ZIP: C:\Users\18160\AppData\Local\Temp\pytest-of-18160\pytest-53\test_full_pipeline_with_real_s0\artifact.zip (4,153 bytes)
PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_can_resume_from_next_chapter PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_architecture_resume_and_plot_arcs_inspection PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_workspace_text_editing_roundtrip PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json 
  ZIP: C:\Users\18160\AppData\Local\Temp\pytest-of-18160\pytest-53\test_full_workflow_json0\bundle.zip (7,339 bytes)
PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_role_library_workflow_and_prompt_injection_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_continue_and_skip_existing_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_clamp_and_distinct_skip_modes_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_resume_and_review_context_commands_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_workspace_and_chapter_write_commands_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_chapter_status_scan_and_project_status_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_config_management_crud_and_choose_json PASSED

======================= 56 passed in 118.45s (0:01:58) ========================
```

Updated summary statistics:

- Total tests: 56
- Pass rate: 100%
- Execution time: 118.45s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, runtime config binding, prompt inspection, architecture resume inspection, plot-arcs review context, direct workspace editing, chapter state inspection, batch generation/continue workflows, role-library CLI CRUD, full `config.json` CRUD for LLM/embedding profiles, and single-profile JSON import with metadata preservation
- Covered: installed-command subprocess verification via `[_resolve_cli] Using installed command:`, selected-profile protection on delete, choose-config rename propagation, and persistence validation that config mutations are truly written to disk
- Remaining gap: live network-backed LLM and embedding providers are still not exercised; deterministic harness mocks continue to validate the real source pipeline without external API calls

## Strict HARNESS Compatibility Verification

Last run: 2026-05-02 18:03:50

Command run:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest -v -s --tb=short cli_anything/ai_novelgenerator/tests
```

Full output:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.0.1, pluggy-1.6.0 -- C:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\Desktop\�¿�\Novel\AI_NovelGenerator\agent-harness
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.3.37, cov-4.1.0
collecting ... [_resolve_cli] Using installed command: C:\Users\18160\AppData\Roaming\Python\Python311\Scripts\cli-anything-ai-novelgenerator.EXE
collected 60 items

cli_anything/ai_novelgenerator/tests/test_core.py::test_create_project_writes_expected_shape PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_load_and_update_project PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_counts_workspace_files PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_important_workspace_paths PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_capture_and_restore_workspace_snapshot PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_session_undo_and_redo_restore_project PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_bundle_writes_valid_zip PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_compat_wrappers_return_expected_metadata PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_list_profiles_groups_project_bound_slots PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_render_compat_uses_bundle_preset PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_export_render_rejects_unknown_preset PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_runtime_config_resolves_mock_profiles PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_profile_crud_and_choose_persist_to_json PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_rename_updates_selected_choose_slots PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_config_import_profile_preserves_extra_metadata_fields PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_harness_mock_llm_blueprint_response_is_parseable PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_info_parses_blueprint_entry PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_returns_chapter_context PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_role_library_crud_and_move PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_import_roles_from_file_parses_multiple_entries PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_analyze_and_import_roles_from_character_state PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_build_prompt_injects_role_library_content PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_generate_chapter_reports_included_roles PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_architecture_resume_state_reports_partial_progress PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_plot_arcs_context_reads_review_context PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_review_consistency_includes_plot_arcs_context PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_finalize_range PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_skip_existing PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_clamp_to_blueprint_range PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_distinguishes_draft_and_finalized_skips PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_batch_generate_chapters_can_auto_enrich_low_word_drafts PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_next_unfinished_and_continue_batch_generation PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_can_clamp_and_skip_finalized PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_continue_batch_generation_reports_when_no_chapter_can_resume PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_chapter_status_and_scan_report_missing_draft_finalized PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_finalized_chapter_summary PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_generate_blueprint_before_chapters PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_recommends_finalizing_existing_draft PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_project_status_reports_complete_when_all_chapters_finalized PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_workspace_text_info_and_write_roundtrip PASSED
cli_anything/ai_novelgenerator/tests/test_core.py::test_write_chapter_text_creates_editable_chapter_file PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_full_pipeline_with_real_source_modules 
  ZIP: C:\Users\18160\AppData\Local\Temp\pytest-of-18160\pytest-67\test_full_pipeline_with_real_s0\artifact.zip (4,158 bytes)
PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_project_status_after_pipeline PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_export_bundle_contains_manifest PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_prompt_inspection_after_first_chapter PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_workflow_creates_multiple_chapters PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_batch_generation_can_resume_from_next_chapter PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_architecture_resume_and_plot_arcs_inspection PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::test_workspace_text_editing_roundtrip PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow_json 
  ZIP: C:\Users\18160\AppData\Local\Temp\pytest-of-18160\pytest-67\test_full_workflow_json0\bundle.zip (7,335 bytes)
PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_prompt_commands_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_generate_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_role_library_workflow_and_prompt_injection_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_continue_and_skip_existing_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_batch_clamp_and_distinct_skip_modes_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_resume_and_review_context_commands_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_workspace_and_chapter_write_commands_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_chapter_status_scan_and_project_status_json PASSED
cli_anything/ai_novelgenerator/tests/test_full_e2e.py::TestCLISubprocess::test_config_management_crud_and_choose_json PASSED

======================= 60 passed in 119.40s (0:01:59) ========================
```

Updated summary statistics:

- Total tests: 60
- Pass rate: 100%
- Execution time: 119.40s

Updated coverage notes:

- Covered: project lifecycle, session snapshots, export bundle creation, compatibility wrappers in `core.project` (`create/open/save/info/list_profiles`), compatibility rendering through `core.export.render()` and `EXPORT_PRESETS`, runtime config binding, prompt inspection, architecture resume inspection, plot-arcs review context, direct workspace editing, chapter state inspection, batch generation/continue workflows, role-library CLI CRUD, and full `config.json` CRUD for LLM/embedding profiles
- Covered: decorator-based centralized CLI error handling, single-profile JSON import with metadata preservation, selected-profile protection on delete, choose-config rename propagation, and installed-command subprocess verification via `[_resolve_cli] Using installed command:`
- Remaining gap: live network-backed LLM and embedding providers are still not exercised; deterministic harness mocks continue to validate the real source pipeline without external API calls
