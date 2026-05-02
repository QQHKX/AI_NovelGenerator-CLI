"""Consistency-review wrappers that preserve JSON-safe CLI output."""

import contextlib
import io
import os

from cli_anything.ai_novelgenerator.core import inspection as inspection_mod
from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import get_runtime_config, patched_adapters, source_modules


def review_consistency(project: dict, chapter_number: int) -> dict:
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    plot_arcs = inspection_mod.plot_arcs_context(project)
    chapter_path = os.path.join(project["workspace_dir"], "chapters", f"chapter_{chapter_number}.txt")
    with patched_adapters(project):
        with contextlib.redirect_stdout(io.StringIO()):
            result = modules["consistency_checker"].check_consistency(
                novel_setting=_read(os.path.join(project["workspace_dir"], "Novel_architecture.txt")),
                character_state=_read(os.path.join(project["workspace_dir"], "character_state.txt")),
                global_summary=_read(os.path.join(project["workspace_dir"], "global_summary.txt")),
                chapter_text=_read(chapter_path),
                api_key=runtime["consistency_review_llm"]["api_key"],
                base_url=runtime["consistency_review_llm"]["base_url"],
                model_name=runtime["consistency_review_llm"]["model_name"],
                temperature=runtime["consistency_review_llm"]["temperature"],
                plot_arcs=plot_arcs["text"],
                interface_format=runtime["consistency_review_llm"]["interface_format"],
                max_tokens=runtime["consistency_review_llm"]["max_tokens"],
                timeout=runtime["consistency_review_llm"]["timeout"],
            )
    return {
        "chapter_number": chapter_number,
        "result": result,
        "chapter_path": chapter_path,
        "plot_arcs_path": plot_arcs["plot_arcs_path"],
        "plot_arcs_included": plot_arcs["review_context_ready"],
    }


def _read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()
