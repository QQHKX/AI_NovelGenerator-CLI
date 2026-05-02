"""Consistency-review wrappers that preserve JSON-safe CLI output."""

import contextlib
import io
import os

from cli_anything.ai_novelgenerator.core import generation as generation_mod
from cli_anything.ai_novelgenerator.core import roles as roles_mod
from cli_anything.ai_novelgenerator.core import inspection as inspection_mod
from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import get_runtime_config, patched_adapters, source_modules


def _progress(callback, scope: str, step: str, current: int | None = None, total: int | None = None, **extra):
    if callback is None:
        return
    callback(scope=scope, step=step, current=current, total=total, **extra)


def review_consistency(project: dict, chapter_number: int, progress_callback=None) -> dict:
    number = generation_mod.validate_chapter_number(project, chapter_number, require_in_blueprint=True)["chapter_number"]
    _progress(progress_callback, "review:consistency", f"第 {number} 章：加载运行时配置")
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    _progress(progress_callback, "review:consistency", f"Chapter {number}: Collecting context")
    plot_arcs = inspection_mod.plot_arcs_context(project)
    chapter_path = os.path.join(project["workspace_dir"], "chapters", f"chapter_{number}.txt")
    chapter_text = _read(chapter_path)
    role_checks = _role_coherence_checks(project, chapter_text)
    theme_checks = _theme_coherence_checks(project, chapter_text)
    _progress(progress_callback, "review:consistency", f"Chapter {number}: Calling model")
    with patched_adapters(project):
        with contextlib.redirect_stdout(io.StringIO()):
            result = modules["consistency_checker"].check_consistency(
                novel_setting=_read(os.path.join(project["workspace_dir"], "Novel_architecture.txt")),
                character_state=_read(os.path.join(project["workspace_dir"], "character_state.txt")),
                global_summary=_read(os.path.join(project["workspace_dir"], "global_summary.txt")),
                chapter_text=chapter_text,
                api_key=runtime["consistency_review_llm"]["api_key"],
                base_url=runtime["consistency_review_llm"]["base_url"],
                model_name=runtime["consistency_review_llm"]["model_name"],
                temperature=runtime["consistency_review_llm"]["temperature"],
                plot_arcs=plot_arcs["text"],
                interface_format=runtime["consistency_review_llm"]["interface_format"],
                max_tokens=runtime["consistency_review_llm"]["max_tokens"],
                timeout=runtime["consistency_review_llm"]["timeout"],
            )
    payload = {
        "chapter_number": number,
        "result": result,
        "chapter_path": chapter_path,
        "plot_arcs_path": plot_arcs["plot_arcs_path"],
        "plot_arcs_included": plot_arcs["review_context_ready"],
        "role_checks": role_checks,
        "theme_checks": theme_checks,
    }
    _progress(progress_callback, "review:consistency", f"Chapter {number}: Completed")
    return payload


def _read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _role_coherence_checks(project: dict, chapter_text: str) -> dict:
    requested_names = [item.strip() for item in str(project["chapter_defaults"].get("characters_involved", "")).replace("，", ",").split(",") if item.strip()]
    role_listing = roles_mod.list_roles(project, roles_mod.ALL_CATEGORY_NAME)
    available_names = {item["name"] for item in role_listing["roles"]}
    missing_roles = [name for name in requested_names if name not in available_names]
    missing_mentions = [name for name in requested_names if name in available_names and name not in chapter_text]
    warnings = []
    if missing_roles:
        warnings.append(f"Requested characters missing from role library: {', '.join(missing_roles)}")
    if missing_mentions:
        warnings.append(f"Requested characters not mentioned in chapter text: {', '.join(missing_mentions)}")
    return {
        "requested_characters": requested_names,
        "missing_role_definitions": missing_roles,
        "missing_chapter_mentions": missing_mentions,
        "warnings": warnings,
    }


def _theme_coherence_checks(project: dict, chapter_text: str) -> dict:
    anchors = [
        str(project["parameters"].get("topic", "")).strip(),
        str(project["parameters"].get("genre", "")).strip(),
        str(project["chapter_defaults"].get("user_guidance", "")).strip(),
    ]
    anchors = [item for item in anchors if item]
    missing_anchors = []
    for anchor in anchors:
        keywords = [part for part in anchor.replace("，", " ").replace(",", " ").split() if part]
        if keywords and not any(keyword in chapter_text for keyword in keywords):
            missing_anchors.append(anchor)
    warnings = []
    if missing_anchors:
        warnings.append(f"Theme anchors not reflected directly in chapter text: {', '.join(missing_anchors)}")
    return {
        "theme_anchors": anchors,
        "missing_theme_anchors": missing_anchors,
        "warnings": warnings,
    }
