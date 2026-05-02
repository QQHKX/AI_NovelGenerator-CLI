"""Export helpers and render-compatibility wrappers.

The source application does not expose a dedicated headless render pipeline, so
the harness currently packages the project and workspace into deterministic ZIP
artifacts. `render()` and `EXPORT_PRESETS` provide a compatibility surface for
callers that expect a generic rendering API.
"""

import json
import os
import zipfile
from pathlib import Path

from cli_anything.ai_novelgenerator.core.project import important_workspace_paths, project_status


EXPORT_PRESETS = {
    "bundle": {
        "format": "zip",
        "description": "Archive the project JSON and workspace files into a ZIP bundle.",
    }
}


def export_bundle(project: dict, project_path: str, output_path: str, overwrite: bool = False) -> dict:
    output = os.path.abspath(output_path)
    if os.path.exists(output) and not overwrite:
        raise RuntimeError(f"Output already exists: {output}")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    workspace = project["workspace_dir"]
    manifest = {
        "project_path": os.path.abspath(project_path),
        "project_name": project["name"],
        "status": project_status(project),
        "important_paths": important_workspace_paths(project),
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.write(project_path, arcname="project.json")
        if os.path.isdir(workspace):
            for root, _, names in os.walk(workspace):
                for name in names:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, workspace)
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
    }


def render(project: dict, project_path: str, output_path: str, preset: str = "bundle", overwrite: bool = False) -> dict:
    """Compatibility wrapper for export-style rendering.

    The only supported preset today is `bundle`, which maps to ZIP bundle export.
    """
    normalized = str(preset).strip().lower()
    if normalized != "bundle":
        raise RuntimeError(f"Unsupported export preset: {preset}. Available presets: {', '.join(sorted(EXPORT_PRESETS))}")
    result = export_bundle(project, project_path, output_path, overwrite=overwrite)
    result["requested_preset"] = preset
    return result
