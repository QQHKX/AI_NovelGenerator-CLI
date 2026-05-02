"""Export helpers and render-compatibility wrappers.

The source application does not expose a dedicated headless render pipeline, so
the harness currently packages the project and workspace into deterministic ZIP
artifacts. `render()` and `EXPORT_PRESETS` provide a compatibility surface for
callers that expect a generic rendering API.
"""

import json
import os
import re
import zipfile
from pathlib import Path

from cli_anything.ai_novelgenerator.core import configuration as configuration_mod
from cli_anything.ai_novelgenerator.core import generation as generation_mod
from cli_anything.ai_novelgenerator.core.project import important_workspace_paths, project_status


EXPORT_PRESETS = {
    "bundle": {
        "format": "zip",
        "description": "Archive the project JSON and workspace files into a ZIP bundle.",
    },
    "manuscript": {
        "format": "md",
        "description": "Assemble all chapters into a complete manuscript file.",
    }
}

_SENSITIVE_NAME_PATTERNS = [
    re.compile(r"^\.env($|\.)", re.IGNORECASE),
    re.compile(r"^config\.json$", re.IGNORECASE),
    re.compile(r".*credentials.*\.json$", re.IGNORECASE),
    re.compile(r".*secrets?.*\.json$", re.IGNORECASE),
    re.compile(r".*(api[_-]?key|token|secret|credential).*$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
]


def export_bundle(project: dict, project_path: str, output_path: str, overwrite: bool = False) -> dict:
    output = os.path.abspath(output_path)
    if os.path.exists(output) and not overwrite:
        raise RuntimeError(f"Output already exists: {output}")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    workspace = project["workspace_dir"]
    manifest = {
        "project_path": os.path.abspath(project_path),
        "project_name": project["name"],
        "config": configuration_mod.safe_config_reference(project["config_path"]),
        "status": project_status(project),
        "important_paths": important_workspace_paths(project),
    }
    skipped_files = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.write(project_path, arcname="project.json")
        if os.path.isdir(workspace):
            for root, _, names in os.walk(workspace):
                for name in names:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, workspace)
                    if _is_sensitive_workspace_file(full, rel):
                        skipped_files.append(rel)
                        continue
                    archive.write(full, arcname=str(Path("workspace") / rel))
    size = os.path.getsize(output)
    with open(output, "rb") as handle:
        magic = handle.read(4)
    return {
        "output": output,
        "file_size": size,
        "magic_bytes": magic.hex(),
        "format": "zip",
        "preset": "bundle",
        "skipped_sensitive_files": skipped_files,
    }


def render(project: dict, project_path: str, output_path: str, preset: str = "bundle", overwrite: bool = False) -> dict:
    """Compatibility wrapper for export-style rendering.

    The only supported preset today is `bundle`, which maps to ZIP bundle export.
    """
    normalized = str(preset).strip().lower()
    if normalized == "manuscript":
        result = export_manuscript(project, output_path, overwrite=overwrite)
        result["requested_preset"] = preset
        return result
    if normalized != "bundle":
        raise RuntimeError(f"Unsupported export preset: {preset}. Available presets: {', '.join(sorted(EXPORT_PRESETS))}")
    result = export_bundle(project, project_path, output_path, overwrite=overwrite)
    result["requested_preset"] = preset
    return result


def export_manuscript(project: dict, output_path: str, overwrite: bool = False, format_name: str = "md") -> dict:
    output = os.path.abspath(output_path)
    if os.path.exists(output) and not overwrite:
        raise RuntimeError(f"Output already exists: {output}")
    format_name = str(format_name).strip().lower()
    if format_name not in {"md", "txt"}:
        raise RuntimeError("Manuscript export format must be 'md' or 'txt'.")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    blueprint = generation_mod.validate_blueprint(project, require_complete=True)
    parts = _render_manuscript(project, blueprint["chapter_numbers"], format_name=format_name)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(parts)
    return {
        "output": output,
        "format": format_name,
        "preset": "manuscript",
        "chapter_count": len(blueprint["chapter_numbers"]),
        "blueprint_path": blueprint["path"],
    }


def _render_manuscript(project: dict, chapter_numbers: list[int], format_name: str) -> str:
    blueprint_path = os.path.join(project["workspace_dir"], "Novel_directory.txt")
    with open(blueprint_path, "r", encoding="utf-8") as handle:
        blueprint_text = handle.read()
    parser = __import__("chapter_directory_parser")
    sections = []
    title = project.get("name", "novel-project")
    if format_name == "md":
        sections.append(f"# {title}\n")
        sections.append(f"- Topic: {project['parameters'].get('topic', '')}")
        sections.append(f"- Genre: {project['parameters'].get('genre', '')}")
        sections.append(f"- Chapters: {project['parameters'].get('num_chapters', 0)}\n")
    else:
        sections.append(f"{title}\n")
        sections.append(f"主题: {project['parameters'].get('topic', '')}\n")
        sections.append(f"类型: {project['parameters'].get('genre', '')}\n")
        sections.append(f"章节数: {project['parameters'].get('num_chapters', 0)}\n")
    for chapter_number in chapter_numbers:
        chapter_path = os.path.join(project["workspace_dir"], "chapters", f"chapter_{chapter_number}.txt")
        if not os.path.exists(chapter_path):
            raise RuntimeError(f"Cannot export manuscript because chapter file is missing: {chapter_path}")
        chapter_info = parser.get_chapter_info_from_blueprint(blueprint_text, chapter_number)
        title_line = f"第{chapter_number}章 {chapter_info.get('chapter_title', '').strip()}".strip()
        text = Path(chapter_path).read_text(encoding="utf-8").strip()
        if format_name == "md":
            sections.append(f"## {title_line}\n\n{text}\n")
        else:
            sections.append(f"{title_line}\n\n{text}\n")
    return "\n".join(sections).strip() + "\n"


def _is_sensitive_workspace_file(full_path: str, relative_path: str) -> bool:
    normalized_rel = str(relative_path).replace("\\", "/")
    if normalized_rel.startswith("vectorstore/"):
        return False
    filename = os.path.basename(full_path)
    return any(pattern.match(filename) or pattern.match(normalized_rel) for pattern in _SENSITIVE_NAME_PATTERNS)
