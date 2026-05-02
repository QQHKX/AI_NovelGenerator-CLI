"""Read-only inspection helpers for blueprint, prompt, and resume state."""

import contextlib
import io
import importlib
import os

from cli_anything.ai_novelgenerator.core import project as project_mod
from cli_anything.ai_novelgenerator.core import roles as roles_mod
from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import get_runtime_config, patched_adapters, source_modules


def chapter_info(project: dict, chapter_number: int) -> dict:
    modules = source_modules(project["source_root"])
    parser = importlib.import_module("chapter_directory_parser")
    blueprint_path = os.path.join(project["workspace_dir"], "Novel_directory.txt")
    blueprint_text = _read_text(blueprint_path)
    info = parser.get_chapter_info_from_blueprint(blueprint_text, int(chapter_number))
    return {
        "chapter_number": int(chapter_number),
        "blueprint_path": blueprint_path,
        "blueprint_exists": os.path.exists(blueprint_path),
        "chapter_info": info,
        "recent_chapter_files": _recent_chapter_files(project["workspace_dir"], int(chapter_number)),
        "status": project_mod.project_status(project),
        "source_module": modules["chapter_module"].__name__,
    }


def build_prompt(project: dict, chapter_number: int) -> dict:
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    parser = importlib.import_module("chapter_directory_parser")
    workspace_dir = project["workspace_dir"]
    blueprint_path = os.path.join(workspace_dir, "Novel_directory.txt")
    blueprint_text = _read_text(blueprint_path)
    number = int(chapter_number)

    with patched_adapters(project):
        # The source app prints verbose prompt/debug output to stdout.
        # Swallow it here so CLI `--json` remains valid machine-readable output.
        with contextlib.redirect_stdout(io.StringIO()):
            prompt_text = modules["chapter_module"].build_chapter_prompt(
                api_key=runtime["prompt_draft_llm"]["api_key"],
                base_url=runtime["prompt_draft_llm"]["base_url"],
                model_name=runtime["prompt_draft_llm"]["model_name"],
                filepath=workspace_dir,
                novel_number=number,
                word_number=int(project["parameters"]["word_number"]),
                temperature=runtime["prompt_draft_llm"]["temperature"],
                user_guidance=project["chapter_defaults"]["user_guidance"],
                characters_involved=project["chapter_defaults"]["characters_involved"],
                key_items=project["chapter_defaults"]["key_items"],
                scene_location=project["chapter_defaults"]["scene_location"],
                time_constraint=project["chapter_defaults"]["time_constraint"],
                embedding_api_key=runtime["embedding"]["api_key"],
                embedding_url=runtime["embedding"]["base_url"],
                embedding_interface_format=runtime["embedding"]["interface_format"],
                embedding_model_name=runtime["embedding"]["model_name"],
                embedding_retrieval_k=int(project["chapter_defaults"]["embedding_retrieval_k"]),
                interface_format=runtime["prompt_draft_llm"]["interface_format"],
                max_tokens=runtime["prompt_draft_llm"]["max_tokens"],
                timeout=runtime["prompt_draft_llm"]["timeout"],
            )

    injected = roles_mod.inject_role_library_into_prompt(project, prompt_text, project["chapter_defaults"]["characters_involved"])
    prompt_text = injected["prompt_text"]

    return {
        "chapter_number": number,
        "prompt_text": prompt_text,
        "prompt_length": len(prompt_text),
        "blueprint_path": blueprint_path,
        "chapter_info": parser.get_chapter_info_from_blueprint(blueprint_text, number),
        "next_chapter_info": parser.get_chapter_info_from_blueprint(blueprint_text, number + 1),
        "recent_chapter_files": _recent_chapter_files(workspace_dir, number),
        "knowledge_files": project_mod.project_status(project)["knowledge_files"],
        "included_roles": injected["included_roles"],
    }


def architecture_resume_state(project: dict) -> dict:
    modules = source_modules(project["source_root"])
    workspace_dir = project["workspace_dir"]
    partial_path = os.path.join(workspace_dir, "partial_architecture.json")
    partial_exists = os.path.exists(partial_path)
    partial_data = modules["architecture_module"].load_partial_architecture_data(workspace_dir)

    steps = [
        ("core_seed_result", "core_seed"),
        ("character_dynamics_result", "character_dynamics"),
        ("character_state_result", "character_state"),
        ("world_building_result", "world_building"),
        ("plot_arch_result", "plot_architecture"),
    ]
    completed_steps = [name for key, name in steps if partial_data.get(key)]
    next_step = next((name for key, name in steps if not partial_data.get(key)), None)
    architecture_path = os.path.join(workspace_dir, "Novel_architecture.txt")
    character_state_path = os.path.join(workspace_dir, "character_state.txt")

    if partial_exists and partial_data:
        state = "in_progress"
    elif os.path.exists(architecture_path):
        state = "completed"
    else:
        state = "not_started"

    return {
        "workspace_dir": workspace_dir,
        "partial_architecture_path": partial_path,
        "partial_architecture_exists": partial_exists,
        "resume_available": bool(partial_exists and partial_data),
        "state": state,
        "completed_steps": completed_steps,
        "next_step": next_step,
        "architecture_exists": os.path.exists(architecture_path),
        "character_state_exists": os.path.exists(character_state_path),
        "raw_data": partial_data,
    }


def plot_arcs_context(project: dict) -> dict:
    workspace_dir = project["workspace_dir"]
    plot_arcs_path = os.path.join(workspace_dir, "plot_arcs.txt")
    text = _read_text(plot_arcs_path)
    entries = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        "plot_arcs_path": plot_arcs_path,
        "exists": os.path.exists(plot_arcs_path),
        "text": text,
        "line_count": len(entries),
        "review_context_ready": bool(text.strip()),
    }


def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _recent_chapter_files(workspace_dir: str, chapter_number: int) -> list[str]:
    chapters_dir = os.path.join(workspace_dir, "chapters")
    files = []
    start = max(1, int(chapter_number) - 3)
    for current in range(start, int(chapter_number)):
        path = os.path.join(chapters_dir, f"chapter_{current}.txt")
        if os.path.exists(path):
            files.append(path)
    return files
