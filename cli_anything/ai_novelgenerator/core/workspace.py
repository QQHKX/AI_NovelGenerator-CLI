"""Direct read/write helpers for editable workspace text artifacts."""

import os


_WORKSPACE_FILES = {
    "architecture": "Novel_architecture.txt",
    "blueprint": "Novel_directory.txt",
    "character-state": "character_state.txt",
    "global-summary": "global_summary.txt",
}


def workspace_text_info(project: dict, target: str) -> dict:
    name = _normalize_target(target)
    path = _workspace_path(project, name)
    text = _read_text(path)
    return _text_payload(name, path, text)


def write_workspace_text(project: dict, target: str, text: str) -> dict:
    name = _normalize_target(target)
    path = _workspace_path(project, name)
    _write_text(path, text)
    return _text_payload(name, path, text)


def chapter_text_info(project: dict, chapter_number: int) -> dict:
    path = _chapter_path(project, chapter_number)
    text = _read_text(path)
    payload = _text_payload("chapter", path, text)
    payload["chapter_number"] = int(chapter_number)
    return payload


def write_chapter_text(project: dict, chapter_number: int, text: str) -> dict:
    path = _chapter_path(project, chapter_number)
    _write_text(path, text)
    payload = _text_payload("chapter", path, text)
    payload["chapter_number"] = int(chapter_number)
    return payload


def _workspace_path(project: dict, target: str) -> str:
    filename = _WORKSPACE_FILES.get(target)
    if not filename:
        raise RuntimeError(f"Unsupported workspace target: {target}")
    return os.path.join(project["workspace_dir"], filename)


def _chapter_path(project: dict, chapter_number: int) -> str:
    return os.path.join(project["workspace_dir"], "chapters", f"chapter_{int(chapter_number)}.txt")


def _normalize_target(target: str) -> str:
    name = str(target).strip().lower()
    if name not in _WORKSPACE_FILES:
        allowed = ", ".join(sorted(_WORKSPACE_FILES))
        raise RuntimeError(f"Unsupported workspace target: {target}. Expected one of: {allowed}")
    return name


def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _text_payload(target: str, path: str, text: str) -> dict:
    stripped = text.strip()
    lines = text.splitlines()
    return {
        "target": target,
        "path": path,
        "exists": os.path.exists(path),
        "text": text,
        "char_count": len(text),
        "line_count": len(lines),
        "word_count": len(stripped),
        "preview": stripped[:200],
    }
