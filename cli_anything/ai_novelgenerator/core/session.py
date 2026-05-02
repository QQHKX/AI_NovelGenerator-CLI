"""Session persistence and undo/redo snapshot helpers.

The session layer stores the current project pointer, command history, and
workspace snapshots used for undo/redo. Snapshot capture is intentionally scoped
to text and JSON artifacts managed by the harness so the workflow stays cheap and
predictable while leaving heavyweight generated vector stores alone.
"""

import json
import os
import time
from pathlib import Path


SESSION_DIR = Path.home() / ".cli-anything-ai_novelgenerator"
SESSION_PATH = SESSION_DIR / "session.json"
MAX_HISTORY = 40


def _locked_save_json(path, data, **dump_kwargs) -> None:
    path = str(path)
    try:
        handle = open(path, "r+", encoding="utf-8")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        handle = open(path, "w", encoding="utf-8")
    with handle:
        locked = False
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            pass
        try:
            handle.seek(0)
            handle.truncate()
            json.dump(data, handle, **dump_kwargs)
            handle.flush()
        finally:
            if locked:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _managed_workspace_files(workspace_dir: str) -> list[str]:
    if not os.path.isdir(workspace_dir):
        return []
    files = []
    for root, _, names in os.walk(workspace_dir):
        if os.path.basename(root) == "vectorstore":
            continue
        for name in names:
            if name.endswith((".txt", ".json", ".md")):
                files.append(os.path.join(root, name))
    files.sort()
    return files


def capture_workspace_snapshot(workspace_dir: str) -> dict:
    data = {}
    for path in _managed_workspace_files(workspace_dir):
        rel = os.path.relpath(path, workspace_dir)
        with open(path, "r", encoding="utf-8") as handle:
            data[rel] = handle.read()
    return data


def restore_workspace_snapshot(workspace_dir: str, snapshot: dict) -> None:
    os.makedirs(workspace_dir, exist_ok=True)
    existing = set()
    for path in _managed_workspace_files(workspace_dir):
        existing.add(os.path.relpath(path, workspace_dir))
    desired = set(snapshot)
    for rel in existing - desired:
        os.remove(os.path.join(workspace_dir, rel))
    for rel, content in snapshot.items():
        target = os.path.join(workspace_dir, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(content)


class Session:
    def __init__(self, path: Path | None = None):
        self.path = path or SESSION_PATH
        self.data = self._load()

    def _default(self) -> dict:
        return {
            "current_project": None,
            "history": [],
            "undo": [],
            "redo": [],
            "updated_at": time.time(),
        }

    def _load(self) -> dict:
        if not self.path.is_file():
            return self._default()
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return self._default()

    def save(self) -> str:
        self.data["updated_at"] = time.time()
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        _locked_save_json(self.path, self.data, ensure_ascii=False, indent=2, sort_keys=True)
        return str(self.path)

    def set_current_project(self, project_path: str | None) -> None:
        self.data["current_project"] = os.path.abspath(project_path) if project_path else None
        self.save()

    def add_history(self, command: str) -> None:
        history = self.data.setdefault("history", [])
        history.append({"time": time.time(), "command": command})
        if len(history) > MAX_HISTORY:
            del history[:-MAX_HISTORY]
        self.save()

    def checkpoint(self, project_path: str, project_data: dict) -> None:
        workspace = project_data.get("workspace_dir", "")
        with open(project_path, "r", encoding="utf-8") as handle:
            project_json = handle.read()
        snap = {
            "time": time.time(),
            "project_path": os.path.abspath(project_path),
            "project_json": project_json,
            "workspace_dir": workspace,
            "workspace": capture_workspace_snapshot(workspace),
        }
        undo = self.data.setdefault("undo", [])
        undo.append(snap)
        if len(undo) > MAX_HISTORY:
            del undo[:-MAX_HISTORY]
        self.data["redo"] = []
        self.save()

    def _restore(self, snap: dict) -> dict:
        project_path = snap["project_path"]
        os.makedirs(os.path.dirname(project_path), exist_ok=True)
        with open(project_path, "w", encoding="utf-8") as handle:
            handle.write(snap["project_json"])
        restore_workspace_snapshot(snap["workspace_dir"], snap.get("workspace", {}))
        self.set_current_project(project_path)
        return {
            "project_path": project_path,
            "workspace_dir": snap["workspace_dir"],
        }

    def undo(self, current_project_path: str, current_project_data: dict) -> dict:
        undo = self.data.setdefault("undo", [])
        if not undo:
            raise RuntimeError("No undo snapshot available")
        current = {
            "time": time.time(),
            "project_path": os.path.abspath(current_project_path),
            "project_json": json.dumps(current_project_data, ensure_ascii=False, indent=2, sort_keys=True),
            "workspace_dir": current_project_data["workspace_dir"],
            "workspace": capture_workspace_snapshot(current_project_data["workspace_dir"]),
        }
        self.data.setdefault("redo", []).append(current)
        snap = undo.pop()
        result = self._restore(snap)
        self.save()
        return result

    def redo(self, current_project_path: str, current_project_data: dict) -> dict:
        redo = self.data.setdefault("redo", [])
        if not redo:
            raise RuntimeError("No redo snapshot available")
        current = {
            "time": time.time(),
            "project_path": os.path.abspath(current_project_path),
            "project_json": json.dumps(current_project_data, ensure_ascii=False, indent=2, sort_keys=True),
            "workspace_dir": current_project_data["workspace_dir"],
            "workspace": capture_workspace_snapshot(current_project_data["workspace_dir"]),
        }
        self.data.setdefault("undo", []).append(current)
        snap = redo.pop()
        result = self._restore(snap)
        self.save()
        return result

    def status(self) -> dict:
        return {
            "session_path": str(self.path),
            "current_project": self.data.get("current_project"),
            "undo_depth": len(self.data.get("undo", [])),
            "redo_depth": len(self.data.get("redo", [])),
            "history_depth": len(self.data.get("history", [])),
            "updated_at": self.data.get("updated_at"),
        }
