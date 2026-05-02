"""Project control-file helpers and compatibility wrappers.

This module manages the harness-side project JSON that points at an
AI_NovelGenerator workspace. It also exposes a small compatibility layer using
generic names like `create`, `open`, `save`, and `info` so callers do not need
to know the harness' internal function naming.
"""

import builtins
import json
import os
import time
from pathlib import Path

from cli_anything.ai_novelgenerator.core import configuration as configuration_mod
from cli_anything.ai_novelgenerator.core import generation as generation_mod
from cli_anything.ai_novelgenerator.core import roles as roles_mod


SCHEMA_VERSION = 1
SOFTWARE_NAME = "AI_NovelGenerator"


PROFILE_GROUPS = {
    "llm": [
        "architecture_llm",
        "chapter_outline_llm",
        "prompt_draft_llm",
        "final_chapter_llm",
        "consistency_review_llm",
    ],
    "embedding": ["embedding"],
}


def now_ts() -> float:
    return time.time()


def default_source_root() -> str:
    return str(Path(__file__).resolve().parents[1] / "backend" / "source_root")


def default_project(name: str, workspace_dir: str, config_path: str, source_root: str | None = None) -> dict:
    source = os.path.abspath(source_root or default_source_root())
    workspace = os.path.abspath(workspace_dir)
    config = os.path.abspath(config_path)
    ts = now_ts()
    return {
        "schema_version": SCHEMA_VERSION,
        "software": SOFTWARE_NAME,
        "name": name,
        "created_at": ts,
        "updated_at": ts,
        "source_root": source,
        "config_path": config,
        "workspace_dir": workspace,
        "parameters": {
            "topic": "",
            "genre": "",
            "num_chapters": 10,
            "word_number": 3000,
        },
        "profiles": {
            "architecture_llm": None,
            "chapter_outline_llm": None,
            "prompt_draft_llm": None,
            "final_chapter_llm": None,
            "consistency_review_llm": None,
            "embedding": None,
        },
        "chapter_defaults": {
            "user_guidance": "",
            "characters_involved": "",
            "key_items": "",
            "scene_location": "",
            "time_constraint": "",
            "embedding_retrieval_k": 4,
        },
        "last_outputs": {},
    }


def ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def save_project(project: dict, project_path: str) -> str:
    project["updated_at"] = now_ts()
    ensure_parent_dir(project_path)
    with builtins.open(project_path, "w", encoding="utf-8") as handle:
        json.dump(project, handle, ensure_ascii=False, indent=2, sort_keys=True)
    return os.path.abspath(project_path)


def load_project(project_path: str) -> dict:
    with builtins.open(project_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def create_project(
    project_path: str,
    name: str,
    workspace_dir: str,
    config_path: str,
    source_root: str | None = None,
    topic: str = "",
    genre: str = "",
    num_chapters: int = 10,
    word_number: int = 3000,
) -> dict:
    project = default_project(name, workspace_dir, config_path, source_root=source_root)
    project["parameters"].update(
        {
            "topic": topic,
            "genre": genre,
            "num_chapters": int(num_chapters),
            "word_number": int(word_number),
        }
    )
    os.makedirs(project["workspace_dir"], exist_ok=True)
    save_project(project, project_path)
    project["project_path"] = os.path.abspath(project_path)
    return project


def update_project(project: dict, **changes) -> dict:
    for key, value in changes.items():
        if value is None:
            continue
        if key in project.get("parameters", {}):
            project["parameters"][key] = value
        elif key in project.get("profiles", {}):
            project["profiles"][key] = value
        elif key in project.get("chapter_defaults", {}):
            project["chapter_defaults"][key] = value
        else:
            project[key] = value
    project["updated_at"] = now_ts()
    return project


def _file_info(path: str) -> dict:
    exists = os.path.exists(path)
    return {
        "path": path,
        "exists": exists,
        "size": os.path.getsize(path) if exists and os.path.isfile(path) else 0,
    }


def _recommended_progress_action(chapter_scan: dict, architecture_exists: bool, blueprint_exists: bool) -> dict:
    if not architecture_exists:
        return {
            "next_action": "generate_architecture",
            "recommended_next_chapter": None,
            "reason": "Novel architecture has not been generated yet.",
        }
    if not blueprint_exists:
        return {
            "next_action": "generate_blueprint",
            "recommended_next_chapter": None,
            "reason": "Chapter blueprint has not been generated yet.",
        }

    chapters = chapter_scan.get("chapters", [])
    first_missing = next((item for item in chapters if item["state"] == "missing"), None)
    if first_missing is not None:
        return {
            "next_action": "generate_chapter",
            "recommended_next_chapter": first_missing["chapter_number"],
            "reason": "The next missing chapter should be drafted.",
        }

    first_draft = next((item for item in chapters if item["state"] == "draft"), None)
    if first_draft is not None:
        return {
            "next_action": "finalize_chapter",
            "recommended_next_chapter": first_draft["chapter_number"],
            "reason": "A drafted chapter is available for finalization.",
        }

    return {
        "next_action": "project_complete",
        "recommended_next_chapter": None,
        "reason": "All configured chapters are finalized.",
    }


def _role_library_summary(project: dict) -> dict:
    categories = roles_mod.list_categories(project)["categories"]
    visible_categories = [name for name in categories if name != roles_mod.TEMP_LIBRARY_NAME]
    role_listing = roles_mod.list_roles(project, roles_mod.ALL_CATEGORY_NAME)
    requested_names = [item.strip() for item in str(project["chapter_defaults"].get("characters_involved", "")).replace("，", ",").split(",") if item.strip()]
    available_names = {item["name"] for item in role_listing["roles"]}
    included_names = [name for name in requested_names if name in available_names]
    missing_names = [name for name in requested_names if name not in available_names]
    return {
        "roles_root": role_listing["roles_root"],
        "category_count": len(visible_categories),
        "categories": visible_categories,
        "role_count": role_listing["role_count"],
        "roles": [item["name"] for item in role_listing["roles"]],
        "requested_characters": requested_names,
        "available_requested_characters": included_names,
        "missing_requested_characters": missing_names,
    }


def project_status(project: dict) -> dict:
    workspace = project["workspace_dir"]
    chapters_dir = os.path.join(workspace, "chapters")
    chapter_files = []
    if os.path.isdir(chapters_dir):
        for name in sorted(os.listdir(chapters_dir)):
            if name.startswith("chapter_") and name.endswith(".txt"):
                chapter_files.append(name)
    knowledge_files = []
    for name in sorted(os.listdir(workspace)) if os.path.isdir(workspace) else []:
        if name.lower().endswith((".txt", ".md")) and name not in {
            "Novel_architecture.txt",
            "Novel_directory.txt",
            "character_state.txt",
            "global_summary.txt",
        }:
            knowledge_files.append(name)
    configured_total = int(project["parameters"].get("num_chapters", 0))
    chapter_state_path = os.path.join(workspace, "chapter_states.json")
    finalized_chapters = generation_mod._load_chapter_state(project)["finalized_chapters"]
    chapter_scan = generation_mod.scan_chapter_statuses(project, 1, configured_total) if configured_total > 0 else {
        "chapter_count": 0,
        "missing_count": 0,
        "draft_count": 0,
        "finalized_count": 0,
        "chapters": [],
    }
    architecture = _file_info(os.path.join(workspace, "Novel_architecture.txt"))
    blueprint = _file_info(os.path.join(workspace, "Novel_directory.txt"))
    next_step = _recommended_progress_action(chapter_scan, architecture_exists=architecture["exists"], blueprint_exists=blueprint["exists"])
    role_library = _role_library_summary(project)
    result = {
        "name": project["name"],
        "workspace_dir": workspace,
        "config": configuration_mod.safe_config_reference(project["config_path"]),
        "source_root": project["source_root"],
        "parameters": project["parameters"],
        "profiles": project["profiles"],
        "architecture": architecture,
        "blueprint": blueprint,
        "character_state": _file_info(os.path.join(workspace, "character_state.txt")),
        "global_summary": _file_info(os.path.join(workspace, "global_summary.txt")),
        "partial_architecture": _file_info(os.path.join(workspace, "partial_architecture.json")),
        "chapter_states": _file_info(chapter_state_path),
        "vectorstore_exists": os.path.isdir(os.path.join(workspace, "vectorstore")),
        "chapter_count": len(chapter_files),
        "chapter_files": chapter_files,
        "finalized_chapter_count": len(finalized_chapters),
        "finalized_chapters": finalized_chapters,
        "chapter_state_counts": {
            "missing": chapter_scan["missing_count"],
            "draft": chapter_scan["draft_count"],
            "finalized": chapter_scan["finalized_count"],
        },
        "next_action": next_step["next_action"],
        "recommended_next_chapter": next_step["recommended_next_chapter"],
        "next_action_reason": next_step["reason"],
        "knowledge_files": knowledge_files,
        "role_library": role_library,
        "last_outputs": project.get("last_outputs", {}),
    }
    return result


def important_workspace_paths(project: dict) -> dict:
    workspace = project["workspace_dir"]
    return {
        "workspace_dir": workspace,
        "architecture": os.path.join(workspace, "Novel_architecture.txt"),
        "blueprint": os.path.join(workspace, "Novel_directory.txt"),
        "character_state": os.path.join(workspace, "character_state.txt"),
        "global_summary": os.path.join(workspace, "global_summary.txt"),
        "partial_architecture": os.path.join(workspace, "partial_architecture.json"),
        "plot_arcs": os.path.join(workspace, "plot_arcs.txt"),
        "roles_dir": os.path.join(workspace, "角色库"),
        "chapters_dir": os.path.join(workspace, "chapters"),
        "vectorstore_dir": os.path.join(workspace, "vectorstore"),
    }


def create(project_path: str, **kwargs) -> dict:
    """Compatibility wrapper for project creation."""
    return create_project(project_path, **kwargs)


def open(project_path: str) -> dict:
    """Compatibility wrapper for loading a project from disk."""
    project = load_project(project_path)
    project["project_path"] = os.path.abspath(project_path)
    return project


def save(project: dict, project_path: str) -> dict:
    """Compatibility wrapper for persisting a project and returning metadata."""
    saved_path = save_project(project, project_path)
    return {
        "project_path": saved_path,
        "name": project.get("name"),
        "saved": True,
        "updated_at": project.get("updated_at"),
    }


def info(project: dict, project_path: str | None = None) -> dict:
    """Return project metadata plus resolved status and optional path."""
    payload = dict(project)
    payload["config"] = configuration_mod.safe_config_reference(project["config_path"])
    payload.pop("config_path", None)
    if project_path:
        payload["project_path"] = os.path.abspath(project_path)
    payload["status"] = project_status(project)
    payload["important_paths"] = important_workspace_paths(project)
    return payload


def list_profiles(project: dict) -> dict:
    """Summarize configured profile bindings from the project file.

    This reports the project-local slot bindings grouped by profile type. It is a
    compatibility surface for harnesses that expect project modules to expose a
    `list_profiles` helper.
    """
    profiles = project.get("profiles", {})
    grouped = {}
    for profile_type, slots in PROFILE_GROUPS.items():
        grouped[profile_type] = [
            {"slot": slot, "selected": profiles.get(slot)}
            for slot in slots
        ]
    return {
        "profile_groups": grouped,
        "profiles": dict(profiles),
    }
