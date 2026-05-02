# AI_NovelGenerator Harness SOP

## Backend Engine

The GUI in `main.py` is a `customtkinter` shell around source-native Python modules:

- `novel_generator/architecture.py`: novel architecture generation
- `novel_generator/blueprint.py`: chapter blueprint generation
- `novel_generator/chapter.py`: prompt building and draft generation
- `novel_generator/finalization.py`: chapter finalization and vector-store updates
- `novel_generator/knowledge.py`: knowledge import
- `consistency_checker.py`: consistency review

The harness wraps those modules directly instead of reimplementing the workflow.

## Native Data Model

The application persists project state as files inside a workspace directory:

- `Novel_architecture.txt`
- `Novel_directory.txt`
- `character_state.txt`
- `global_summary.txt`
- `partial_architecture.json`
- `chapter_states.json`
- `chapters/chapter_<n>.txt`
- `vectorstore/`

The harness project JSON is an agent-facing control file that points at that native workspace.

## GUI To CLI Mapping

- `Step1. Generate Settings` -> `generate architecture`
- `Step2. Generate Directory` -> `generate blueprint`
- `角色库` window category bar / role list / editor / import dialog -> `role categories|list|show|create|rename|delete|move|import-file|analyze-state|import-state`
- `配置面板` LLM profiles / Embedding profiles / choose config selectors -> `config llm|embedding|choose ...`
- `Novel Architecture` / `Chapter Blueprint` / `Character State` / `Global Summary` manual tabs -> `workspace show|write`
- `Step3. Generate Chapter Draft` -> `chapter generate`
- `Step3. Generate Multiple Chapters` -> `chapter batch`
- `Step3. Generate Multiple Chapters` enhanced controls -> `chapter batch --skip-existing --auto-enrich --min-words ...` and `chapter continue`
- `Chapters Manage` manual save -> `chapter write`
- `Step3 prompt preview / chapter metadata inspection` -> `chapter prompt` / `chapter info` / `chapter status` / `chapter scan`
- `Step4. Finalize Current Chapter` -> `chapter finalize`
- `Consistency Proofread` -> `review consistency`
- Knowledge import UI -> `knowledge import`

## CLI Design

Command groups match the app domains:

- `project`: create/open/update/status with finalized-chapter summary
- `config`: inspect runtime config, project-local profile overrides, and full `config.json` CRUD for LLM/embedding profiles plus choose-config persistence
- `generate`: architecture and blueprint
- `generate architecture-state`: inspect resumable `partial_architecture.json` progress and next step
- `workspace`: read/write direct text edits for core workspace files
- `role`: category and role-library lifecycle management, source-file import, and `character_state.txt` analysis/import
- `chapter`: info/prompt/status/scan/draft/batch/continue/finalize/show/write/list/enrich
- `knowledge`: import/clear/status
- `review`: consistency checks and `plot_arcs.txt` inspection
- `export`: zip bundle export
- `session`: persistent project pointer and undo/redo snapshots

## Current Refinement Coverage

- Added prompt-inspection coverage around `novel_generator.chapter.build_chapter_prompt`
- Added parsed blueprint inspection coverage around `chapter_directory_parser.get_chapter_info_from_blueprint`
- Added sequential batch chapter generation with optional per-chapter finalization
- Added batch-generation parity features for skip-existing, auto-enrich, configurable minimum-word threshold, and continue-from-next-unfinished workflows
- Added blueprint-aware batch range clamping and distinct draft-vs-finalized skip policies backed by harness-managed per-chapter finalization state
- Added per-chapter state inspection for `missing` / `draft` / `finalized` and surfaced finalized chapter summaries through `project status`
- Added lightweight workflow recommendations in `project status` via `next_action` and `recommended_next_chapter`
- Added explainable continue-batch responses that report why resume starts at a chapter and which earlier chapters were skipped
- Added resumable partial-architecture inspection around `novel_generator.architecture.load_partial_architecture_data`
- Added `plot_arcs.txt` inspection and passed that context through consistency review
- Added direct read/write coverage for `Novel_architecture.txt`, `Novel_directory.txt`, `character_state.txt`, `global_summary.txt`, and chapter text files
- The harness can now expose agent-readable chapter metadata and the exact generated prompt before a chapter draft is created
- Added full role-library CLI coverage for category creation, role listing, create/rename/delete/move, source-file import, `character_state.txt` analysis, and importing analyzed roles into the persistent library
- Added harness-side prompt injection parity so named roles from `workspace/角色库` are inserted into the generated chapter prompt just like the GUI flow
- Added subprocess coverage for the end-to-end role-library workflow and validated `included_roles` in both `chapter prompt` and `chapter generate` JSON responses
- Added role-library summary visibility to `project status`, including requested-vs-available character matching for prompt injection readiness
- Added real `config.json` management coverage for listing, creating, updating, renaming, and deleting LLM/embedding profiles
- Added choose-config inspection and persistence coverage for current selected LLM slots and embedding profile, including rename propagation when a selected profile is renamed
- Added single-profile JSON import coverage for LLM and embedding configs so GUI-created metadata fields like `id` and timestamps can be preserved during CLI backup/restore flows

## State Model

- Project state persists in `<project>.json`
- Native novel content persists in `workspace_dir`
- Session metadata persists in `~/.cli-anything-ai_novelgenerator/session.json`
- Undo/redo snapshots capture the harness project JSON plus managed text/JSON workspace files

## Backend Strategy

There is no pre-existing headless app CLI, so the harness uses the real source modules as the backend.
For deterministic tests, the harness supplies a `HarnessMock` adapter path by patching the app's LLM and embedding factory functions at runtime. This still executes the real generation pipeline and file-writing logic.

## Rendering Gap Assessment

The harness now exposes a compatibility rendering surface through `core.export.render()` and `EXPORT_PRESETS`, but this should be treated as an API-shape bridge rather than parity with media-oriented render harnesses.

- Current rendered artifact: `bundle` preset only
- Actual backend behavior: ZIP packaging of the project control file plus workspace artifacts
- Observable guarantee: valid ZIP output with manifest metadata, project JSON, and workspace file payloads
- Why this is acceptable here: `AI_NovelGenerator` is a text-workspace application with no native final media renderer, timeline engine, or document conversion backend to invoke

What is covered now:

- Generic callers can use `render(project, project_path, output_path, preset="bundle")`
- Preset discovery is possible through `EXPORT_PRESETS`
- Tests verify output existence, ZIP magic bytes, manifest presence, and overwrite handling

What remains a gap:

- No native `pdf`, `epub`, `docx`, `html`, or reader-facing manuscript export preset exists in the source application
- No alternate rendering presets map to distinct backend pipelines because the source tree does not expose them
- No visual preview or publication-layout render step is currently available

Implication for future refinement:

- If the source project later adds a real publication/export backend, `render()` should become the stable compatibility entry point that dispatches to those native formats
- Until then, the harness documents render support as bundle export compatibility, not as a full manuscript publishing surface
