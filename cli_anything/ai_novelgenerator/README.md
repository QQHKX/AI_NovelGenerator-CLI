# cli-anything-ai-novelgenerator

Standalone CLI workflow harness for `AI_NovelGenerator`.

This package wraps the novel-generation pipeline behind a scriptable command line interface. It is designed for automation, batch workflows, prompt inspection, workspace editing, and deterministic testing.

## Status

- Standalone: the package now vendors the runtime backend it needs and no longer requires a sibling `AI_NovelGenerator` source checkout.
- Scope: this is a workflow CLI, not a publication renderer.
- Export support: current export parity is `bundle` only, which writes a ZIP archive of the project file and workspace artifacts.

## Install

Editable install:

```bash
pip install -e .
```

Regular install with test extras:

```bash
pip install .[test]
```

The installed command is:

```bash
cli-anything-ai-novelgenerator
```

## Quick Start

Create a config file and project:

```bash
cli-anything-ai-novelgenerator project new -o demo.json --workspace ./demo-work --config ./config.json --topic "记忆之城" --genre "科幻" --chapters 3 --words 1200
```

Run the main workflow:

```bash
cli-anything-ai-novelgenerator --project demo.json generate architecture
cli-anything-ai-novelgenerator --project demo.json generate blueprint
cli-anything-ai-novelgenerator --project demo.json chapter generate 1
cli-anything-ai-novelgenerator --project demo.json chapter finalize 1
cli-anything-ai-novelgenerator --project demo.json export bundle ./demo.zip --overwrite
```

Run with `--json` for machine-readable output:

```bash
cli-anything-ai-novelgenerator --json --project demo.json project status
```

Run with no arguments to enter the REPL:

```bash
cli-anything-ai-novelgenerator
```

## Command Groups

- `project`: create, open, update, inspect, and track project progress
- `config`: inspect runtime config, manage LLM and embedding profiles, and bind selections
- `generate`: generate architecture and blueprint, inspect resumable architecture state
- `workspace`: inspect and overwrite core workspace text files
- `role`: manage role-library categories and entries, import and analyze character state
- `chapter`: inspect prompts and metadata, generate drafts, batch generate, continue, finalize, enrich, and edit chapter text
- `knowledge`: import and clear vector-store content
- `review`: run consistency review and inspect plot-arc context
- `export`: export a ZIP bundle
- `session`: persist current project pointer and support undo/redo snapshots

## Config Notes

The CLI works against a JSON config file referenced by each project. You can either:

- manage the file directly with `--config-path`
- manage the project-bound config with `--project`

Profile CRUD is fully scriptable:

```bash
cli-anything-ai-novelgenerator --json --project demo.json config llm list
cli-anything-ai-novelgenerator --json --project demo.json config llm create StoryLLM --api-key mock --base-url mock://llm --model-name story-model --temperature 0.3 --max-tokens 8192 --timeout 60 --interface-format HarnessMock
cli-anything-ai-novelgenerator --json --project demo.json config choose set --architecture-llm StoryLLM --chapter-outline-llm StoryLLM --prompt-draft-llm StoryLLM --final-chapter-llm StoryLLM --consistency-review-llm StoryLLM --embedding MockEmbedding
```

## Useful Workflows

Prompt inspection before mutation:

```bash
cli-anything-ai-novelgenerator --json --project demo.json chapter info 2
cli-anything-ai-novelgenerator --json --project demo.json chapter prompt 2
cli-anything-ai-novelgenerator --json --project demo.json chapter status 2
```

Batch generation:

```bash
cli-anything-ai-novelgenerator --json --project demo.json chapter batch 1 10 --finalize --skip-existing --auto-enrich --min-words 1500
cli-anything-ai-novelgenerator --json --project demo.json chapter continue 10 --clamp-to-blueprint --skip-finalized
```

Workspace editing:

```bash
cli-anything-ai-novelgenerator --json --project demo.json workspace show architecture
cli-anything-ai-novelgenerator --json --project demo.json workspace write blueprint --text "修订后的章节蓝图"
cli-anything-ai-novelgenerator --json --project demo.json chapter write 3 --text "第3章人工修订内容"
```

## Testing

Run the test suite from `agent-harness/`:

```bash
python -m pytest
```

To force subprocess tests to use the installed console script rather than the module fallback:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest
```

The suite uses deterministic `HarnessMock` adapters so it can exercise the real workflow without external API calls.

## Limitations

- Live external providers are not exercised in the default test suite.
- Export currently targets ZIP bundle output only.
- The CLI is optimized for automation and headless workflows, not GUI parity in presentation.
